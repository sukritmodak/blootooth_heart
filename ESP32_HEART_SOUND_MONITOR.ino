#include <Arduino.h>
#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

#define ANALOG_PIN 34
#define DIGITAL_PIN 27
#define BEAT_STATE LOW
#define MIN_SOUND_GAP 150UL
#define MIN_S1_S2_GAP 100UL
#define MAX_S1_S2_GAP 500UL
#define MIN_S1_INTERVAL 273UL
#define MAX_S1_INTERVAL 2000UL
#define BPM_HISTORY_SIZE 5
#define BPM_OUTPUT_MS 1000UL
#define SAMPLE_RATE 4000UL
const unsigned long SAMPLE_INTERVAL = 1000000UL / SAMPLE_RATE;

enum HeartState { WAITING_FOR_FIRST_S1, WAITING_FOR_S2, WAITING_FOR_NEXT_S1 };
HeartState heartState = WAITING_FOR_FIRST_S1;
int previousDigitalState = HIGH;
unsigned long lastSoundTime=0,currentS1Time=0,previousS1Time=0,lastBpmOutput=0;
unsigned long totalSoundNumber=0,totalHeartBeatNumber=0;
bool havePreviousS1=false;
float bpmHistory[BPM_HISTORY_SIZE];
int bpmHistoryCount=0,bpmHistoryIndex=0;
float measuredBpm=NAN;

void BT(const String &m){SerialBT.println(m);}

void addBpm(float bpm){
  if(!isfinite(bpm)||bpm<30.0f||bpm>220.0f)return;
  bpmHistory[bpmHistoryIndex]=bpm;
  bpmHistoryIndex=(bpmHistoryIndex+1)%BPM_HISTORY_SIZE;
  if(bpmHistoryCount<BPM_HISTORY_SIZE)bpmHistoryCount++;
  float sum=0;
  for(int i=0;i<bpmHistoryCount;i++)sum+=bpmHistory[i];
  measuredBpm=sum/bpmHistoryCount;
}

void registerS1(unsigned long t){
  if(havePreviousS1){
    unsigned long interval=t-previousS1Time;
    if(interval>=MIN_S1_INTERVAL&&interval<=MAX_S1_INTERVAL){
      float instantBpm=60000.0f/(float)interval;
      addBpm(instantBpm);
      BT("S1-S1 interval = "+String(interval)+" ms");
      BT("Instant BPM = "+String(instantBpm,1));
    }else BT("S1-S1 interval rejected = "+String(interval)+" ms");
  }else BT("First S1 accepted; waiting for next S1");
  previousS1Time=t;
  havePreviousS1=true;
  currentS1Time=t;
  totalHeartBeatNumber++;
  BT("S1 detected");
  BT("S1 #"+String(totalHeartBeatNumber));
}

void processSound(unsigned long t){
  if(lastSoundTime!=0&&t-lastSoundTime<MIN_SOUND_GAP)return;
  lastSoundTime=t;
  totalSoundNumber++;

  if(heartState==WAITING_FOR_FIRST_S1){
    registerS1(t); heartState=WAITING_FOR_S2; return;
  }

  if(heartState==WAITING_FOR_S2){
    unsigned long gap=t-currentS1Time;
    if(gap>=MIN_S1_S2_GAP&&gap<=MAX_S1_S2_GAP){
      BT("S2 detected");
      BT("S1-S2 gap = "+String(gap)+" ms");
      BT("Sound #"+String(totalSoundNumber));
      BT("--------------------------------");
      heartState=WAITING_FOR_NEXT_S1;
    }else if(gap>MAX_S1_S2_GAP){
      BT("S2 not confirmed; new S1 detected");
      registerS1(t); heartState=WAITING_FOR_S2;
    }
    return;
  }

  registerS1(t);
  heartState=WAITING_FOR_S2;
}

#define AUDIO_BLOCK 128
uint8_t audioBuffer[AUDIO_BLOCK];
int audioIndex=0;
unsigned long nextSampleTime=0;

void sendAudioBlock(){
  uint8_t checksum=0;
  Serial.write(0xA5); Serial.write(0x5A); Serial.write((uint8_t)AUDIO_BLOCK);
  for(int i=0;i<AUDIO_BLOCK;i++){Serial.write(audioBuffer[i]);checksum+=audioBuffer[i];}
  Serial.write(checksum);
}

void setup(){
  Serial.begin(115200);
  SerialBT.begin("ESP32-HEART");
  pinMode(ANALOG_PIN,INPUT);
  pinMode(DIGITAL_PIN,INPUT);
  nextSampleTime=micros();
  lastBpmOutput=millis();
  BT("========================================");
  BT("ESP32 HEART SOUND MONITOR");
  BT("BPM method: S1-to-S1 interval");
  BT("S1-S2 is used only for pairing");
  BT("BPM is NOT calculated from 5-second count");
  BT("Reference BPM = 72");
  BT("========================================");
}

void loop(){
  unsigned long now=millis();
  int digitalState=digitalRead(DIGITAL_PIN);
  if(previousDigitalState==HIGH&&digitalState==BEAT_STATE)processSound(now);
  previousDigitalState=digitalState;

  if(now-lastBpmOutput>=BPM_OUTPUT_MS){
    lastBpmOutput=now;
    if(isfinite(measuredBpm)){
      BT("");
      BT("========== MEASURED BPM ==========");
      BT("BPM = "+String(measuredBpm,1));
      BT("Reference BPM = 72");
      BT("Difference = "+String(measuredBpm-72.0f,1));
      BT("==================================");
      BT("");
    }
  }

  unsigned long currentMicros=micros();
  if((long)(currentMicros-nextSampleTime)>=0){
    nextSampleTime+=SAMPLE_INTERVAL;
    audioBuffer[audioIndex++]=(uint8_t)(analogRead(ANALOG_PIN)>>4);
    if(audioIndex>=AUDIO_BLOCK){sendAudioBlock();audioIndex=0;}
  }
}
