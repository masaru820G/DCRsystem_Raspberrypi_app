# サクランボ病害虫鳥獣被害果除去システム 弐号機 Raspberrypi側の制御フォルダ
## 環境
- Python 3.12

## 使用パッケージ
- "flask>=3.1.2"
- "RPO.GPIO"

## 手順
1. ラズパイとPCを同じローカルネットワークにつなげる(ラズパイ側でホットスポットを立てる)
2. PC側でmainを実行

## プログラム解説
### main_raspi.py
- ラズパイ側でずっと実行しているmainプログラム
- Flaskで該当のURLが送られてくるたび各動作を行う
  
### module_turntable_control.py
- モータの各処理を担当するmodule
