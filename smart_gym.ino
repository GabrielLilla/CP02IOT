/*
 * ============================================================
 *  Smart Gym — Leitor RFID
 *  Checkpoint 02 | Physical Computing (IoT & IoB) | FIAP
 * ============================================================
 *  Grupo:
 *    Gabriel Terra Lilla dos Santos  RM554575
 *    Fernando Navajas Moraes        RM555080
 *    Wesley Cardoso                 RM557927
 *    José Guilherme Sipaúba Costa   RM557274
 *    Bruna da Costa Candeias        RM558938
 * ============================================================
 *
 *  Funcionamento:
 *    Quando um cartão/tag RFID é aproximado ao módulo MFRC522,
 *    o Arduino lê os 4 bytes do UID, formata como string
 *    hexadecimal separada por espaços (ex: "2A 63 4C 73") e
 *    envia via Serial (9600 baud) para o Python processar.
 *
 *  Conexão MFRC522 → Arduino Uno:
 *    SDA  → Pino 10
 *    SCK  → Pino 13
 *    MOSI → Pino 11
 *    MISO → Pino 12
 *    RST  → Pino 9
 *    GND  → GND
 *    3.3V → 3.3V  ⚠️ NÃO conecte ao 5V — danifica o módulo!
 *
 *  Bibliotecas necessárias (Arduino IDE → Gerenciar Bibliotecas):
 *    - MFRC522 (por GithubCommunity)
 *    - SPI (já inclusa no Arduino IDE)
 * ============================================================
 */

#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN  10   // Pino SDA (Slave Select)
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
  // Aguarda um novo cartão ser aproximado
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
      uid += " ";  // Separador entre bytes
    }
  }

  uid.toUpperCase();  // Garante letras maiúsculas (ex: "2A" e não "2a")

  // Envia o UID via Serial para o Python
  Serial.println(uid);

  // Encerra a comunicação com o cartão atual
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Pequeno delay para evitar leitura dupla do mesmo cartão
  delay(1500);
}
