"""Converts a LuisaRender EXR (linear colour) to an 8-bit sRGB PNG.   python exr_to_png.py render.exr out.png"""
import os, sys
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"   # must be set before importing cv2
import cv2
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
im = np.clip(cv2.imread(src, cv2.IMREAD_UNCHANGED)[:, :, :3], 0, None)
srgb = np.where(im <= 0.0031308, 12.92 * im, 1.055 * np.power(np.clip(im, 1e-8, None), 1 / 2.4) - 0.055)
cv2.imwrite(dst, (np.clip(srgb, 0, 1) * 255).astype(np.uint8))
