// Circuits DIY
// For Complete Details Visit -> https://circuits-diy.com
// Circuit diagram https://derfernstudent.de/arduino-temperaturmessung-mit-dem-lm335/

const int sensorPin = A0;
float sensorValue;
float voltageOut;

float temperatureC;
float temperatureK;
float ave_temp;
float cloop = 50;

void setup() {
  pinMode(sensorPin, INPUT);
  Serial.begin(9600);
}

void loop() {
  ave_temp = 0;
  for (int cc = 0 ; cc < cloop; cc++){
    temperatureK = analogRead(0) * 0.004882812 * 100;
    temperatureC = temperatureK - 65.3 - 273.15;
    ave_temp += temperatureC;
    delay(10);
  }
  Serial.println(ave_temp / cloop);
}