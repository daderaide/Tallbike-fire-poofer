Poofer control info:

relay box specs:

ADC model: ADS1015  
ADC I2C address: 0x48 (address pin tied to ground)  
A0 - pressure sensor  
A1 - ignitor battery monitor (4.2V max)  
A2 - valve battery monitor (12.6V through voltage divider = 3.737V - 0.2966 ratio)  

Relay Board model: PCF8574A  
Relay Board I2C address: 0x3F  

ESP32 board model: ESP32-S3-DevKitC-1 v1.1  

SDA: pin 1 - GPIO1  
SCL: pin 2 - GPIO2  

UART (MAX485):

TX: pin 10 - GPIO17 (UART1)  
RX: pin 11 -  GPIO18 (UART1)  
DE/RE: pin 4 - GPIO4  
