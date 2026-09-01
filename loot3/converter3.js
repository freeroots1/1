#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);

const DISPLAY_WIDTH = 1200;
const DISPLAY_HEIGHT = 1600;
const DITHER_FACTOR = 0.85;

const WENTING = ["#2e2c42", "#d3d6cd", "#d9c701", "#b11d19", "#316ac1", "#5c8a5b"];
const RGB = ["#000000", "#ffffff", "#ffff00", "#ff0000", "#0000ff", "#00ff00"];
const FULL = WENTING.concat(RGB);
const SPECTRA = WENTING;

const PALETTE_TO_NIBBLE = [0x0, 0x1, 0x2, 0x3, 0x5, 0x6];
const WEIGHTS_FLOYD = [
  { dx: 1, dy: 0, w: 7 / 16 },
  { dx: -1, dy: 1, w: 3 / 16 },
  { dx: 0, dy: 1, w: 5 / 16 },
  { dx: 1, dy: 1, w: 1 / 16 },
];

const RGB_TO_LRGB = new Float32Array(256);
for (let i = 0; i < 256; i += 1) {
  RGB_TO_LRGB[i] = v2lrgb(i);
}

const spectraPalette = SPECTRA.map(hex2rgb);
const errPalette = FULL.map(hex2rgb);
const distPalette = FULL.map((hex) => {
  const pixel = hex2rgb(hex);
  rgb2cielab(pixel[0], pixel[1], pixel[2], pixel);
  return pixel;
});

export async function convertImageToBin(inputPath, outputPath = null) {
  const rgba = await loadAndFitImage(inputPath, DISPLAY_WIDTH, DISPLAY_HEIGHT);
  ditherRgbCielabFull(rgba, DISPLAY_WIDTH, DISPLAY_HEIGHT);
  const bin = getDitheredImageBin(rgba, DISPLAY_WIDTH, DISPLAY_HEIGHT);

  const finalOutputPath = outputPath ?? replaceExtension(inputPath, ".bin");
  await fs.writeFile(finalOutputPath, bin);

  return {
    inputPath: path.resolve(inputPath),
    outputPath: path.resolve(finalOutputPath),
    width: DISPLAY_WIDTH,
    height: DISPLAY_HEIGHT,
    bytesWritten: bin.length,
  };
}

export function ditherRgbCielabFull(data, width, height) {
  const paddedW = width + 2;
  const paddedH = height + 1;

  const errBuff = new Float32Array(paddedW * paddedH * 3);
  const errPixel = new Float32Array(3);
  const distPixel = new Float32Array(3);

  for (let y = 0; y < height; y += 1) {
    const row = y * width;
    for (let x = 0; x < width; x += 1) {
      const dIdx = (row + x) * 4;

      errPixel[0] = data[dIdx];
      errPixel[1] = data[dIdx + 1];
      errPixel[2] = data[dIdx + 2];

      if (DITHER_FACTOR > 0) {
        const eIdx = (y * paddedW + x) * 3;
        errPixel[0] += errBuff[eIdx];
        errPixel[1] += errBuff[eIdx + 1];
        errPixel[2] += errBuff[eIdx + 2];
      }

      distPixel[0] = errPixel[0];
      distPixel[1] = errPixel[1];
      distPixel[2] = errPixel[2];
      rgb2cielab(distPixel[0], distPixel[1], distPixel[2], distPixel);

      const paletteIdx = closestCIELABIdx(distPixel, distPalette);
      const difPixel = errPalette[paletteIdx];

      if (DITHER_FACTOR > 0) {
        const err0 = (errPixel[0] - difPixel[0]) * DITHER_FACTOR;
        const err1 = (errPixel[1] - difPixel[1]) * DITHER_FACTOR;
        const err2 = (errPixel[2] - difPixel[2]) * DITHER_FACTOR;

        for (const weight of WEIGHTS_FLOYD) {
          const nx = x + weight.dx;
          const ny = y + weight.dy;
          const nIdx = (ny * paddedW + nx) * 3;
          errBuff[nIdx] += err0 * weight.w;
          errBuff[nIdx + 1] += err1 * weight.w;
          errBuff[nIdx + 2] += err2 * weight.w;
        }
      }

      const spectraPixel = spectraPalette[paletteIdx % 6];
      data[dIdx] = spectraPixel[0];
      data[dIdx + 1] = spectraPixel[1];
      data[dIdx + 2] = spectraPixel[2];
      data[dIdx + 3] = 255;
    }
  }
}

export function getDitheredImageBin(data, width, height) {
  if ((width * height) % 2 !== 0) {
    throw new Error("BIN packing requires an even number of pixels.");
  }

  const flippedData = new Uint8ClampedArray(data.length);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const srcIndex = (y * width + x) * 4;
      const destX = y;
      const destY = width - 1 - x;
      const destIndex = (destY * height + destX) * 4;

      flippedData[destIndex] = data[srcIndex];
      flippedData[destIndex + 1] = data[srcIndex + 1];
      flippedData[destIndex + 2] = data[srcIndex + 2];
      flippedData[destIndex + 3] = data[srcIndex + 3];
    }
  }

  const binArray = new Uint8Array((width * height) / 2);
  for (let i = 0, j = 0; i < flippedData.length; i += 8, j += 1) {
    const highNibble = rgbToNibble(flippedData[i], flippedData[i + 1], flippedData[i + 2]);
    const lowNibble = rgbToNibble(
      flippedData[i + 4],
      flippedData[i + 5],
      flippedData[i + 6],
    );
    binArray[j] = (highNibble << 4) | lowNibble;
  }

  return binArray;
}

async function loadAndFitImage(inputPath, width, height) {
  const sharpImage = await loadWithSharp(inputPath, width, height);
  if (sharpImage) {
    return sharpImage;
  }

  if (process.platform === "win32") {
    return loadWithPowerShellBitmap(inputPath, width, height);
  }

  throw new Error(
    "No image decoder is available. Install `sharp`, or run this script on Windows where PowerShell/System.Drawing is available.",
  );
}

async function loadWithSharp(inputPath, width, height) {
  let sharp;
  try {
    sharp = require("sharp");
  } catch {
    return null;
  }

  const { data } = await sharp(inputPath)
    .rotate()
    .flatten({ background: "#ffffff" })
    .resize({
      width,
      height,
      fit: "cover",
      position: "centre",
      kernel: sharp.kernel.lanczos3,
    })
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  return new Uint8ClampedArray(data.buffer, data.byteOffset, data.byteLength);
}

function loadWithPowerShellBitmap(inputPath, width, height) {
  const script = `
Add-Type -AssemblyName System.Drawing

$inputPath = $env:CONVERTER_INPUT
$targetWidth = [int]$env:CONVERTER_WIDTH
$targetHeight = [int]$env:CONVERTER_HEIGHT

$image = [System.Drawing.Image]::FromFile($inputPath)
$bitmap = New-Object System.Drawing.Bitmap($targetWidth, $targetHeight, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)

try {
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality

    $displayRatio = [double]$targetWidth / [double]$targetHeight
    $imageRatio = [double]$image.Width / [double]$image.Height

    if ([Math]::Abs($imageRatio - $displayRatio) -lt 1e-6) {
        $scale = [Math]::Min([double]$targetWidth / [double]$image.Width, [double]$targetHeight / [double]$image.Height)
    } else {
        $scale = [Math]::Max([double]$targetWidth / [double]$image.Width, [double]$targetHeight / [double]$image.Height)
    }

    $drawWidth = [double]$image.Width * $scale
    $drawHeight = [double]$image.Height * $scale
    $drawX = ([double]$targetWidth - $drawWidth) / 2.0
    $drawY = ([double]$targetHeight - $drawHeight) / 2.0

    $graphics.DrawImage($image, [float]$drawX, [float]$drawY, [float]$drawWidth, [float]$drawHeight)

    $stream = New-Object System.IO.MemoryStream
    try {
        $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Bmp)
        $bytes = $stream.ToArray()
        [Console]::OpenStandardOutput().Write($bytes, 0, $bytes.Length)
    } finally {
        $stream.Dispose()
    }
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $image.Dispose()
}
`;

  const encodedScript = Buffer.from(script, "utf16le").toString("base64");

  const result = spawnSync(
    "powershell",
    ["-NoProfile", "-NonInteractive", "-EncodedCommand", encodedScript],
    {
      maxBuffer: 64 * 1024 * 1024,
      env: {
        ...process.env,
        CONVERTER_INPUT: path.resolve(inputPath),
        CONVERTER_WIDTH: String(width),
        CONVERTER_HEIGHT: String(height),
      },
    },
  );

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    const stderr = result.stderr?.toString("utf8").trim();
    throw new Error(stderr || "PowerShell image preprocessing failed.");
  }

  return decodeBmpToRgba(result.stdout);
}

function decodeBmpToRgba(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length < 54) {
    throw new Error("Invalid BMP data.");
  }
  if (buffer.toString("ascii", 0, 2) !== "BM") {
    throw new Error("Expected BMP data from the image preprocessing step.");
  }

  const dataOffset = buffer.readUInt32LE(10);
  const width = buffer.readInt32LE(18);
  const rawHeight = buffer.readInt32LE(22);
  const bitsPerPixel = buffer.readUInt16LE(28);
  const compression = buffer.readUInt32LE(30);

  if (bitsPerPixel !== 24 || compression !== 0) {
    throw new Error(`Unsupported BMP format: ${bitsPerPixel}bpp compression=${compression}.`);
  }

  const height = Math.abs(rawHeight);
  const topDown = rawHeight < 0;
  const rowSize = Math.floor((bitsPerPixel * width + 31) / 32) * 4;
  const rgba = new Uint8ClampedArray(width * height * 4);

  for (let y = 0; y < height; y += 1) {
    const srcY = topDown ? y : height - 1 - y;
    const rowStart = dataOffset + srcY * rowSize;
    for (let x = 0; x < width; x += 1) {
      const src = rowStart + x * 3;
      const dest = (y * width + x) * 4;
      rgba[dest] = buffer[src + 2];
      rgba[dest + 1] = buffer[src + 1];
      rgba[dest + 2] = buffer[src];
      rgba[dest + 3] = 255;
    }
  }

  return rgba;
}

function hex2rgb(hex) {
  hex = hex.replace("#", "");
  return [
    Number.parseInt(hex.slice(0, 2), 16),
    Number.parseInt(hex.slice(2, 4), 16),
    Number.parseInt(hex.slice(4, 6), 16),
  ];
}

function v2lrgb(value) {
  value /= 255;
  return value > 0.04045 ? Math.pow((value + 0.055) / 1.055, 2.4) : value / 12.92;
}

function rgb2lrgb(r, g, b, out) {
  if (
    r >= 0 && r <= 255 && Number.isInteger(r) &&
    g >= 0 && g <= 255 && Number.isInteger(g) &&
    b >= 0 && b <= 255 && Number.isInteger(b)
  ) {
    out[0] = RGB_TO_LRGB[r];
    out[1] = RGB_TO_LRGB[g];
    out[2] = RGB_TO_LRGB[b];
    return;
  }

  out[0] = v2lrgb(r);
  out[1] = v2lrgb(g);
  out[2] = v2lrgb(b);
}

function lrgb2cielab(r, g, b, out) {
  const xn = 0.95047;
  const yn = 1.0;
  const zn = 1.08883;

  let x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375;
  let y = r * 0.2126729 + g * 0.7151522 + b * 0.072175;
  let z = r * 0.0193339 + g * 0.119192 + b * 0.9503041;

  x /= xn;
  y /= yn;
  z /= zn;

  x = x > 0.008856 ? Math.cbrt(x) : 7.787037 * x + 4 / 29;
  y = y > 0.008856 ? Math.cbrt(y) : 7.787037 * y + 4 / 29;
  z = z > 0.008856 ? Math.cbrt(z) : 7.787037 * z + 4 / 29;

  out[0] = 116 * y - 16;
  out[1] = 500 * (x - y);
  out[2] = 200 * (y - z);
}

function rgb2cielab(r, g, b, out) {
  rgb2lrgb(r, g, b, out);
  lrgb2cielab(out[0], out[1], out[2], out);
}

function closestCIELABIdx(pixel, palette) {
  let minDist = Infinity;
  let closestIndex = 0;

  for (let i = 0; i < palette.length; i += 1) {
    const color = palette[i];
    const dL = color[0] - pixel[0];
    const dA = color[1] - pixel[1];
    const dB = color[2] - pixel[2];
    const dist = 2 * dL * dL + dA * dA + dB * dB;

    if (dist < minDist) {
      minDist = dist;
      closestIndex = i;
    }
  }

  return closestIndex;
}

function rgbToNibble(r, g, b) {
  for (let i = 0; i < spectraPalette.length; i += 1) {
    const color = spectraPalette[i];
    if (r === color[0] && g === color[1] && b === color[2]) {
      return PALETTE_TO_NIBBLE[i];
    }
  }
  throw new Error(`Color ${r}, ${g}, ${b} not found in spectra palette.`);
}

function replaceExtension(filePath, newExtension) {
  const parsed = path.parse(filePath);
  return path.join(parsed.dir, `${parsed.name}${newExtension}`);
}

function parseCliArgs(argv) {
  if (argv.length < 1) {
    throw new Error(
      "Usage: node converter3.js <image_name>\n" +
      "   or: node converter3.js <image_name> <output.bin>",
    );
  }

  const inputPath = argv[0];
  const outputPath = argv[1] ?? null;
  return { inputPath, outputPath };
}

async function main() {
  try {
    const { inputPath, outputPath } = parseCliArgs(process.argv.slice(2));
    const result = await convertImageToBin(inputPath, outputPath);
    console.log(
      `Wrote ${result.outputPath} (${result.width}x${result.height}, ${result.bytesWritten} bytes)`,
    );
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
