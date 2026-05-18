import pigpio

class MotorController:
    """
    モーターの制御ロジック（ハードウェア、状態）をすべてカプセル化するクラス。
    pigpioのWave generation（DMAタイマー）を使用することで、
    OSスケジューラーに依存しない正確なパルスを生成し、異音を防ぐ。
    ※ _で始まる関数はクラス内部専用（Flaskから直接呼ばない）
    """
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpioデーモンに接続できません。ラズパイで 'sudo pigpiod' を実行してください。")

        # GPIOピン設定（BCMピン番号）
        self.DIR_pin = 15
        self.PUL_pin = 17
        self.ENA_pin = 18

        self.pi.set_mode(self.DIR_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.PUL_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.ENA_pin, pigpio.OUTPUT)

        self.pi.write(self.DIR_pin, 0)  # DIR=LOW -> 反時計回り
        self.pi.write(self.PUL_pin, 0)
        self.pi.write(self.ENA_pin, 0)

        # パルスの幅を指定。値が小さいほど高速回転
        # self.motor_delay = 0.0004  # 速い
        # self.motor_delay = 0.0006  # 普通
        self.motor_delay = 0.0008  # 遅い
        '''
        1パルスあたりの時間[s](t) = delay * 2
        1回転あたりのパルス数[回](cnt) = (ratio = 1) * (360 / 1.8) * MICRO_status
        1回転あたりにかかる時間[s](T) = t * cnt
        '''
        self.is_running = False
        self._wave_id = -1  # 現在再生中のwave ID（-1は未生成）

        print("MotorController: 初期化完了。")

    def _motor_enable(self, enable=True):
        self.pi.write(self.ENA_pin, 1 if enable else 0)

    def _create_wave(self):
        """
        現在のmotor_delayに基づいてDMAパルス波形を生成する。
        pigpioのwave generationはDMAで動作するため、CPUやOSの負荷に関係なく
        正確な周期でパルスを出力できる。
        """
        half_period_us = int(self.motor_delay * 1_000_000)  # 秒→マイクロ秒

        self.pi.wave_clear()
        pulses = [
            pigpio.pulse(1 << self.PUL_pin, 0,              half_period_us),  # HIGH
            pigpio.pulse(0,              1 << self.PUL_pin, half_period_us),  # LOW
        ]
        self.pi.wave_add_generic(pulses)
        wave_id = self.pi.wave_create()
        if wave_id < 0:
            raise RuntimeError(f"wave_create()に失敗しました。エラーコード: {wave_id}")
        return wave_id


    # --- Flaskから呼び出される「公開」関数 ---

    def start_rotation(self):
        """モーターの回転を開始する"""
        if self.is_running:
            print("MotorController: 既に回転中です。")
            return False

        print("MotorController: 回転を開始します。")
        self._motor_enable(True)
        self._wave_id = self._create_wave()
        self.pi.wave_send_repeat(self._wave_id)  # 停止命令が来るまで繰り返し再生
        self.is_running = True
        return True

    def stop_rotation(self):
        """モーターの回転を停止させる"""
        if not self.is_running:
            print("MotorController: 既に停止しています。")
            return

        print("MotorController: 停止します。")
        self.pi.wave_tx_stop()
        if self._wave_id >= 0:
            self.pi.wave_delete(self._wave_id)
            self._wave_id = -1
        self._motor_enable(False)
        self.is_running = False

    def set_speed(self, delay):
        """モーター速度を設定する"""
        self.motor_delay = delay
        print(f"MotorController: 速度を {delay} に変更しました。")
        if self.is_running:
            # 回転中の場合は新しい速度で波形を即座に差し替える
            self.pi.wave_tx_stop()
            if self._wave_id >= 0:
                self.pi.wave_delete(self._wave_id)
            self._wave_id = self._create_wave()
            self.pi.wave_send_repeat(self._wave_id)

    def get_status(self):
        """現在の状態を辞書で返す"""
        return {
            "motor_is_running": self.is_running,
            "current_speed_delay": self.motor_delay,
        }

    def cleanup(self):
        """リソースをクリーンアップする"""
        print("MotorController: クリーンアップを実行します。")
        self.stop_rotation()
        self.pi.stop()  # pigpioデーモンとの接続を切断
