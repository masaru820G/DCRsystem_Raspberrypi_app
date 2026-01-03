# -------------------------------------------------
# モーターの各管理を担当するmodule
# -------------------------------------------------
import RPi.GPIO as GPIO
import time
import threading

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
        # GPIO設定 BCM ：コネクタのピン番号を使用
        GPIO.setmode(GPIO.BCM)
        # --- クラス内変数定義 --------------------------------------
        # GPIOピン設定
        #self.DIR_pin = 15
        self.PUL_pin = 17
        #self.ENA_pin = 18

        # GPIOセットアップ設定
        #GPIO.setup(self.DIR_pin, GPIO.OUT, initial=GPIO.LOW)
        #GPIO.output(self.DIR_pin, 0) # DIR=LOW -> 反時計回り
        GPIO.setup(self.PUL_pin, GPIO.OUT, initial=GPIO.LOW)
        #GPIO.setup(self.ENA_pin, GPIO.OUT, initial=GPIO.LOW)

        # パルスの幅を指定。値が小さいほど高速回転
        self.current_pulse_delay = SPEED_MAP[5]     # ボタンにより変わるパルス幅

        self.is_running = False    # モーターの「停止フラグ」 回転を継続中かどうか
        self.motor_thread = None   # スレッドを格納する変数

        print("MotorController: 初期化完了。")


    """
    # --- モーター有効化/無効化関数 --------------------------------------
    def _motor_enable(self, enable=True):   #デフォルト引数: 引数を何も指定せずに呼び出したらenable=Trueとする
        GPIO.output(self.ENA_pin, GPIO.HIGH if enable else GPIO.LOW)
    """


    # --- 1ステップ関数 --------------------------------------
    def _one_step(self):
        GPIO.output(self.PUL_pin, GPIO.LOW)
        time.sleep(self.current_pulse_delay)
        GPIO.output(self.PUL_pin, GPIO.HIGH)
        time.sleep(self.current_pulse_delay)


    # --- モータループ関数 --------------------------------------
    def _motor_loop(self):
        """
        [スレッド専用] is_runningフラグがTrueの間、回転し続ける
        """
        print("【MotorThread】: 開始。モーターを有効化します。")
        #self._motor_enable(True)

        # self.is_running が True の間だけループ(停止フラグ)
        while self.is_running:
            self._one_step()

        print("【MotorThread】: 終了。モーターを無効化します。")
        #self._motor_enable(False)

        self.is_running = False  # 絶対に is_running を False に戻す


    # --- モータを回転させる関数 --------------------------------------
    def start_rotation(self):
        if self.is_running: # TrueやFalseといったbool値は ==Trueを省略するのが一般的
            print("MotorController: 既に回転中です。")
            return False # 既に動いているという報告をするだけ
        print("MotorController: 回転スレッドを開始します。")
        self.is_running = True # 停止フラグを True に
        self.motor_thread = threading.Thread(target=self._motor_loop)
        self.motor_thread.start()
        return True


    # --- モータを停止させる関数 --------------------------------------
    def stop_rotation(self):
        if not self.is_running: # TrueやFalseといったbool値は notをつけるのが一般的
            print("MotorController: 既に停止しています。")
            return
        print("MotorController: 停止フラグを立てます。")
        self.is_running = False # 停止フラグを False に
        self.motor_thread.join() # スレッドの終了を待つ


    # --- delayを設定する関数 --------------------------------------
    def set_speed(self, current_speed):
        self.current_pulse_delay = SPEED_MAP[current_speed]
        print(f"MotorController: 速度を {self.current_pulse_delay} に変更しました。")


    # --- 今のステータスを表示する関数 --------------------------------------
    def get_status(self):
        return {
            "motor_is_running": self.is_running,
            "current_speed_delay": self.current_pulse_delay,
        }


    # --- GPIOをクリーンアップする関数 --------------------------------------
    def cleanup(self):
        print("MotorController: クリーンアップを実行します。")
        self.stop_rotation() # 念のためモーターを止める
        time.sleep(0.1) # スレッドが止まるのを少し待つ
        GPIO.cleanup()