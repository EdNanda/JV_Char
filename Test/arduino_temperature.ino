// Circuits DIY
// For Complete Details Visit -> https://circuits-diy.com
// Circuit diagram https://derfernstudent.de/arduino-temperaturmessung-mit-dem-lm335/

const int sensorPin = A0;
float sensorValue;
float voltageOut;

float temperatureC;
float temperatureK;
float ave_temp;

void setup() {
  pinMode(sensorPin, INPUT);
  Serial.begin(9600);
}

void loop() {
  ave_temp = 0;
  for (int cc = 0 ; cc < 10; cc++){
    sensorValue = analogRead(sensorPin);
    voltageOut = (sensorValue * 5000) / 1024;

    // calculate temperature for LM335
    temperatureK = voltageOut / 10 - 13.07;
    temperatureC = temperatureK - 466.44;
    ave_temp += temperatureC;
    delay(50);
  }
  Serial.println(ave_temp / 10);
}