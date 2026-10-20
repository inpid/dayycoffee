// 온도 센서 → 노트북 USB 시리얼 (STANDARD ROAST(스탠다드로스트)용)
// 부품: Arduino Uno/Nano + MAX31855 열전대 모듈 2개 (K타입 프로브: BT 원두, ET 배기/드럼)
// 라이브러리: Adafruit MAX31855 library
// 출력 형식(한 줄, 4Hz): "BT=201.25,ET=232.50"  → 보레이트 115200
#include <SPI.h>
#include <Adafruit_MAX31855.h>

Adafruit_MAX31855 btProbe(4, 5, 6);   // CLK, CS, DO
Adafruit_MAX31855 etProbe(4, 7, 6);   // CLK, CS, DO (CLK/DO 공유, CS만 분리)

void setup() { Serial.begin(115200); delay(500); }

void loop() {
  double bt = btProbe.readCelsius(), et = etProbe.readCelsius();
  if (!isnan(bt) && !isnan(et)) {
    Serial.print("BT="); Serial.print(bt, 2);
    Serial.print(",ET="); Serial.println(et, 2);
  }
  delay(250);
}
