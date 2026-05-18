# -------------------------------------------------
# モーターの各管理を担当するmodule (pigpio版)
# RPi.GPIOのソフトウェアタイミングによる異音をDMAハードウェア波形で解消
# -------------------------------------------------
import pigpio
import time

# ==========================================================
# 設定: PCから送られるスピード値(1-10) と パルス幅の対応表
# ==========================================================
# レベル5 (0.0006) を基準に、0.0001ずつ増減させる
SPEED_MAP = {
    1: 0.0010,  #   回転遅い
    2: 0.0009,
    3: 0.0008,
    4: 0.0007,
    5: 0.0006,  # 基準 (デフォルト)
    6: 0.0005,
    7: 0.0004,
    8: 0.0003,
    9: 0.0002,
    10: 0.0001  # 回転速い
}

# ==========================================================
# モーター制御クラス
# ==========================================================
class MotorController():
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError(
                "pigpioデーモンに接続できません。"
                "「sudo pigpiod」を実行してからプログラムを起動してください。"
            )

        self.PUL_pin = 27
        self.pi.set_mode(self.PUL_pin, pigpio.OUTPUT)
        self.pi.write(self.PUL_pin, 0)

        self.current_pulse_delay = SPEED_MAP[5]
        self.is_running = False
        self._wave_id = None

        print("MotorController: 初期化完了 (pigpio)。")

    # --- DMAウェーブフォームを構築する関数 ---------------------------
    def _build_wave(self):
        """
        current_pulse_delay に基づいてDMAウェーブフォームを生成する。
        pigpioの波形はマイクロ秒単位で指定する。
        """
        delay_us = max(1, int(self.current_pulse_delay * 1_000_000))

        self.pi.wave_clear()

        wf = [
            pigpio.pulse(1 << self.PUL_pin, 0,               delay_us),  # HIGH
            pigpio.pulse(0,               1 << self.PUL_pin, delay_us),  # LOW
        ]
        self.pi.wave_add_generic(wf)
        return self.pi.wave_create()

    # --- モータを回転させる関数 --------------------------------------
    def start_rotation(self):
        if self.is_running:
            print("MotorController: 既に回転中です。")
            return False

        wave_id = self._build_wave()
        if wave_id < 0:
            print("MotorController: ウェーブフォームの作成に失敗しました。")
            return False

        self._wave_id = wave_id
        self.pi.wave_send_repeat(self._wave_id)
        self.is_running = True
        print("MotorController: 回転を開始しました (DMA波形)。")
        return True

    # --- モータを停止させる関数 --------------------------------------
    def stop_rotation(self):
        if not self.is_running:
            print("MotorController: 既に停止しています。")
            return False

        self.pi.wave_tx_stop()
        self.pi.write(self.PUL_pin, 0)
        self.is_running = False

        if self._wave_id is not None:
            self.pi.wave_delete(self._wave_id)
            self._wave_id = None

        print("MotorController: 停止しました。")
        return True

    # --- delayを設定する関数 --------------------------------------
    def set_speed(self, current_speed):
        if current_speed not in SPEED_MAP:
            print(f"MotorController: 無効な速度値 {current_speed}。1〜10の範囲で指定してください。")
            return False

        self.current_pulse_delay = SPEED_MAP[current_speed]
        print(f"MotorController: 速度を {self.current_pulse_delay} に変更しました。")

        if self.is_running:
            # 回転中は新しい波形をシームレスに切り替える
            new_wave_id = self._build_wave()
            if new_wave_id >= 0:
                # WAVE_MODE_REPEAT_SYNC: 現在の波形の区切りで新波形に切り替え、ステップ抜けを防ぐ
                self.pi.wave_send_using_mode(new_wave_id, pigpio.WAVE_MODE_REPEAT_SYNC)
                if self._wave_id is not None:
                    self.pi.wave_delete(self._wave_id)
                self._wave_id = new_wave_id

        return True

    # --- GPIOをクリーンアップする関数 --------------------------------------
    def cleanup(self):
        print("MotorController: クリーンアップを実行します。")
        self.stop_rotation()
        time.sleep(0.1)
        self.pi.stop()
        return True
