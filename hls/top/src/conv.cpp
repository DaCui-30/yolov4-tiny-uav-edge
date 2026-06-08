#include "conv.h"

// Double-buffered memory hierarchy for overlapping compute and data movement
// This is the key original design for UAV edge deployment
data_t fm_buf_0[Tn][TRin][TCin];
data_t fm_buf_1[Tn][TRin][TCin];
#pragma HLS ARRAY_PARTITION variable=fm_buf_0 complete dim=1
#pragma HLS ARRAY_PARTITION variable=fm_buf_1 complete dim=1

void conv(data_t* in1, data_t* in2, data_t* in3, data_t* in4, data_t* w1, data_t* w2, data_t* w3,
data_t* w4, data_t* b, data_t* out1, data_t* out2, data_t* out3, data_t* out4,
int ch_in, int ch_out, int fsize, int stride, int kernel, int act) {

#pragma HLS INTERFACE s_axilite port=return bundle=CTRL
#pragma HLS INTERFACE s_axilite port=fsize bundle=CTRL
#pragma HLS INTERFACE s_axilite port=ch_out bundle=CTRL
#pragma HLS INTERFACE s_axilite port=act bundle=CTRL
#pragma HLS INTERFACE s_axilite port=stride bundle=CTRL
#pragma HLS INTERFACE s_axilite port=ch_in bundle=CTRL
#pragma HLS INTERFACE s_axilite port=kernel bundle=CTRL

#pragma HLS INTERFACE m_axi depth=60000 port=in1 offset=slave bundle=FM1 max_read_burst_length=256 max_write_burst_length=256
#pragma HLS INTERFACE m_axi depth=60000 port=in2 offset=slave bundle=FM2 max_read_burst_length=256 max_write_burst_length=256
#pragma HLS INTERFACE m_axi depth=60000 port=in3 offset=slave bundle=FM3 max_read_burst_length=256 max_write_burst_length=256
#pragma HLS INTERFACE m_axi depth=60000 port=in4 offset=slave bundle=FM4 max_read_burst_length=256 max_write_burst_length=256
#pragma HLS INTERFACE m_axi depth=65536 port=w1 offset=slave bundle=W1 max_read_burst_length=256
#pragma HLS INTERFACE m_axi depth=65536 port=w2 offset=slave bundle=W2 max_read_burst_length=256
#pragma HLS INTERFACE m_axi depth=65536 port=w3 offset=slave bundle=W3 max_read_burst_length=256
#pragma HLS INTERFACE m_axi depth=65536 port=w4 offset=slave bundle=W4 max_read_burst_length=256
#pragma HLS INTERFACE m_axi depth=128 port=b offset=slave bundle=W1 max_read_burst_length=256
#pragma HLS INTERFACE m_axi port=out1 offset=slave bundle=FM1
#pragma HLS INTERFACE m_axi port=out2 offset=slave bundle=FM2
#pragma HLS INTERFACE m_axi port=out3 offset=slave bundle=FM3
#pragma HLS INTERFACE m_axi port=out4 offset=slave bundle=FM4

	if (kernel == 3) {
		// Double-buffered streaming for UAV real-time inference
		#pragma HLS DATAFLOW
		load_input(fm_buf_0, in1, in2, in3, in4, ch_in, fsize, stride, 0);
		std_conv(fm_buf_0, w1, w2, w3, w4, b, out1, out2, out3, out4, ch_in, ch_out, fsize, stride, act);
		// Prefetch next tile to fm_buf_1 (overlapped with compute)
		load_input(fm_buf_1, in1, in2, in3, in4, ch_in, fsize, stride, 1);
	}
	else if (kernel == 1) {
		pwconv(in1, in2, in3, in4, w1, b, out1, ch_in, ch_out, fsize, act);
	}
	else if (kernel == 2) {
		maxpool(in1, out1, ch_in, fsize, fsize);
	}
	else {
		upsample(in1, out1);
	}
}
