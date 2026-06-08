############################################################
## This file is generated automatically by Vivado HLS.
## Please DO NOT edit it.
## Copyright (C) 1986-2019 Xilinx, Inc. All Rights Reserved.
############################################################
open_project yolov4
set_top conv
add_files src/conv.cpp
add_files src/conv.h
add_files src/maxpool.cpp
add_files src/maxpool.h
add_files src/pwconv.cpp
add_files src/pwconv.h
add_files src/std_conv.cpp
add_files src/std_conv.h
add_files src/upsample.cpp
add_files src/upsample.h
add_files -tb src/pwconv_test.cpp
add_files -tb src/pwconv_test.h
add_files -tb src/sampling_test.cpp
add_files -tb src/sampling_test.h
add_files -tb src/test_tb.cpp
add_files -tb src/winoconv_test.cpp
add_files -tb src/winoconv_test.h
open_solution "solution1"
set_part {xc7z020clg484-1}
create_clock -period 5.5 -name default
#source "./yolov4/solution1/directives.tcl"
csim_design
csynth_design
cosim_design
export_design -rtl verilog -format ip_catalog -version "0.0.0"
