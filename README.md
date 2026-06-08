# UAV YOLOv4-Tiny FPGA Accelerator

FPGA-based accelerator for YOLOv4-tiny object detection, optimized for UAV edge deployment.

## Hardware

- Board: PYNQ-Z2 (Zynq-7020)
- Tool: Vivado HLS 2022.1 + Vitis 2022.1
- Clock: 100 MHz

## Project Structure

```
uav-yolov4-tiny-fpga-accelerator/
├── hls/top/src/     # HLS C++ IP cores
│   ├── conv.cpp     # Convolution operator
│   ├── maxpool.cpp  # Max pooling
│   ├── upsample.cpp # Upsamping
│   └── std_conv.cpp # Standard convolution
├── Vitis/src/       # ARM-side application (C++)
│   ├── main.cpp     # Main application
│   ├── basic_block.h
│   ├── nms.cpp/h   # Non-maximum suppression
│   └── sd_io.cpp/h # SD card I/O
├── tools/predictor/ # Python inference verification
│   ├── yolo.py     # YOLO model
│   ├── bn_merge.py  # Batch normalization fusion
│   └── predict.py   # Prediction script
└── foled_weights/   # BN-fused weights
```

## Performance

| Metric | This Design | CPU (i7-11800H) | GPU (RTX 3060) |
|--------|--------------|---------------------|-------------------|
| FPS | 371 | 7.3 | 65 |
| Power | 2.8W | 45W | 170W |
| Energy Efficiency | 132.5 FPS/W | 0.16 FPS/W | 0.38 FPS/W |

## Resource Utilization

| Resource | Utilization |
|----------|-------------|
| LUT | 70.49% |
| LUTRAM | 41.5% |
| FF | 42.64% |
| BRAM | 67.5% |
| DSP | 100% |

## Usage

### 1. HLS Synthesis

```bash
cd hls/top
vivado_hls -f run_hls.tcl
```

### 2. Generate Bitstream

```bash
vivado project_1.xpr
# Generate bitstream
```

### 3. Vitis Application

```bash
cd Vitis
vitis -workspace workspace
# Build and run on PYNQ-Z2
```

### 4. Python Verification

```bash
cd tools/predictor
python predict.py --image test.jpg --weights ../folded_weights
```

## Application Scenario

Designed for **UAV-based real-time object detection**:
- Search and rescue
- Maritime surveillance
- Infrastructure inspection
- Edge AI deployment

## Citation

If you use this work, please cite:

```bibtex
@mastersthesis{cui2024design,
  title={Design and Implementation of YOLOv4-tiny Accelerator on PYNQ-Z2 for Object Detection in Resource-Constrained Edge Devices Using High-Level Synthesis},
  author={Cui, Da},
  school={Durham University},
  year={2024}
}
```

## License

MIT License - see LICENSE file for details.
