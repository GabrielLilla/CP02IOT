

#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN  10   // Pino SDA
#define RST_PIN  9   // Pino de Reset

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();

  Serial.println("Smart Gym - Leitor RFID pronto.");
  Serial.println("Aproxime o cartao ao leitor...");
}

void loop() {
  // Aguarda um novo cartão
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Monta a string do UID no formato "XX XX XX XX"
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) {
      uid += "0";  // Zero à esquerda para bytes menores que 0x10
    }
    uid += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) {
      uid += " ";  // Separador
    }
  }

  uid.toUpperCase();  // Garante letras maiúsculas

  Serial.println(uid);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(1500);
}
