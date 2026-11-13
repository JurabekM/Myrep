// Zarbxona Pico HSM'ni rp2040js emulyatorida ishga tushiradi: stdin/stdout ↔ USB CDC (ikkilik),
// KUTMOQDA ramkasi ko'rinsa GP14 tugmasini "bosadi" (EMU_TUGMA navbati: ha|rad|yoq).
// EMU_FLASH — oxirgi 4 KB sektor fayli (quvvat uzilishini sinash uchun). Vaqtlar stderr'ga.
import fs from 'fs';
import { Simulator } from '../src/simulator.js';
import { USBCDC } from '../src/usb/cdc.js';
import { ConsoleLogger, LogLevel } from '../src/utils/logging.js';
import { bootromB1 } from './bootrom.js';
import { loadUF2 } from './load-flash.js';

const image = process.argv[2];
const simulator = new Simulator();
const mcu = simulator.rp2040;
mcu.loadBootrom(bootromB1);
mcu.logger = new ConsoleLogger(LogLevel.Error);
loadUF2(image, mcu);

const SEKTOR = 2 * 1024 * 1024 - 4096;
const flashFayl = process.env.EMU_FLASH;
if (flashFayl && fs.existsSync(flashFayl)) mcu.flash.set(fs.readFileSync(flashFayl), SEKTOR);

const navbat = (process.env.EMU_TUGMA ?? '').split(',').filter((x) => x);
const tugma = mcu.gpio[14];
tugma.setInputValue(true);
const sekund = () => simulator.clock.nanos / 1e9;

let bosishTugashi = -1;
let bosishBoshi = -1;
let bosishUz = 0;
let tayyor = false;
const kutilmoqda: number[] = [];
const cdc = new USBCDC(mcu.usbCtrl);
cdc.onDeviceConnected = () => {
  tayyor = true;
  process.stderr.write(`[${sekund().toFixed(3)} s] USB ulandi\n`);
  for (const b of kutilmoqda.splice(0)) cdc.sendSerialByte(b);
};

let chiq: number[] = [];
cdc.onSerialData = (value) => {
  process.stdout.write(Buffer.from(value));
  chiq.push(...value);
  // ramkalarni kuzatish (faqat vaqt va tugma uchun)
  for (;;) {
    const i = chiq.findIndex((b, j) => b === 0x41 && chiq[j + 1] === 0x51);
    if (i < 0 || chiq.length < i + 8) break;
    const n = chiq[i + 6] | (chiq[i + 7] << 8);
    if (chiq.length < i + 12 + n) break;
    const kod = chiq[i + 3];
    process.stderr.write(`[${sekund().toFixed(3)} s] javob kod=0x${kod.toString(16)} n=${n}\n`);
    if (kod === 0x7f) {
      const j = navbat.shift() ?? 'ha';
      if (j !== 'yoq') {
        // oldingi bosish qo'yib yuborilgandan keyin 0,3 s kutib bosamiz
        bosishBoshi = Math.max(sekund(), bosishTugashi) + 0.3;
        bosishUz = j === 'rad' ? 2.5 : 0.15;
      }
    }
    chiq = chiq.slice(i + 12 + n);
  }
};

setInterval(() => {
  if (bosishTugashi >= 0 && sekund() >= bosishTugashi) {
    tugma.setInputValue(true);
    bosishTugashi = -1;
  }
  if (bosishBoshi >= 0 && sekund() >= bosishBoshi) {
    tugma.setInputValue(false);
    bosishTugashi = bosishBoshi + bosishUz;
    bosishBoshi = -1;
  }
}, 1);

process.stdin.on('data', (chunk: Buffer) => {
  process.stderr.write(`[${sekund().toFixed(3)} s] so'rov ${chunk.length} B\n`);
  for (const b of chunk) {
    if (tayyor) cdc.sendSerialByte(b);
    else kutilmoqda.push(b);
  }
});
process.stdin.on('end', () => {
  if (flashFayl) fs.writeFileSync(flashFayl, mcu.flash.slice(SEKTOR, SEKTOR + 4096));
  process.stderr.write(`[${sekund().toFixed(3)} s] tugadi\n`);
  process.exit(0);
});

// rp2040js flash'ga yozishni (SSI) emulyatsiya qilmaydi: ichki dasturning `flash_ish(sahifa)`
// funksiyasini ushlab, sektorni o'chirish + sahifani yozishni shu yerda bajaramiz.
const flashIsh = process.env.EMU_FLASH_ISH ? parseInt(process.env.EMU_FLASH_ISH, 16) : -1;
if (flashIsh >= 0) {
  const core = mcu.core;
  const asl = core.executeInstruction.bind(core);
  core.executeInstruction = () => {
    if (core.PC === (flashIsh & ~1)) {
      const p = core.registers[0];
      mcu.flash.fill(0xff, SEKTOR, SEKTOR + 4096);
      for (let i = 0; i < 256; i++) mcu.flash[SEKTOR + i] = mcu.readUint8(p + i);
      process.stderr.write(`[${sekund().toFixed(3)} s] flash yozildi\n`);
      core.PC = core.LR & ~1;
      return 1;
    }
    return asl();
  };
}

simulator.rp2040.core.PC = 0x10000000;
simulator.execute();
