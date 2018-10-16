import os, sys
if os.path.exists('../../Python-Lib/'):
	sys.path.insert(1, '../../Python-Lib')
import tensorflow as tf

def VGG19(scope, img, reuse = None):
	with tf.variable_scope(scope, reuse = reuse):
		conv1_1 = tf.layers.conv2d       (inputs = img    , filters =  64, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv1_1') # 224
		conv1_2 = tf.layers.conv2d       (inputs = conv1_1, filters =  64, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv1_2') # 224
		pool1   = tf.layers.max_pooling2d(inputs = conv1_2, pool_size = 2, strides = 2)																	 # 112
		conv2_1 = tf.layers.conv2d       (inputs = pool1  , filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv2_1') # 112
		conv2_2 = tf.layers.conv2d       (inputs = conv2_1, filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv2_2') # 112
		pool2   = tf.layers.max_pooling2d(inputs = conv2_2, pool_size = 2, strides = 2)																	 #  56
		conv3_1 = tf.layers.conv2d       (inputs = pool2  , filters = 256, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv3_1') #  56
		conv3_2 = tf.layers.conv2d       (inputs = conv3_1, filters = 256, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv3_2') #  56
		conv3_3 = tf.layers.conv2d       (inputs = conv3_2, filters = 256, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv3_3') #  56
		conv3_4 = tf.layers.conv2d       (inputs = conv3_3, filters = 256, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv3_4') #  56
		pool3   = tf.layers.max_pooling2d(inputs = conv3_4, pool_size = 2, strides = 2)																	 #  28
		conv4_1 = tf.layers.conv2d       (inputs = pool3  , filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv4_1') #  28
		conv4_2 = tf.layers.conv2d       (inputs = conv4_1, filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv4_2') #  28
		conv4_3 = tf.layers.conv2d       (inputs = conv4_2, filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv4_3') #  28
		conv4_4 = tf.layers.conv2d       (inputs = conv4_3, filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv4_4') #  28
		pool4   = tf.layers.max_pooling2d(inputs = conv4_4, pool_size = 2, strides = 2)																	 #  14
		conv5_1 = tf.layers.conv2d       (inputs = pool4  , filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv5_1') #  14
		conv5_2 = tf.layers.conv2d       (inputs = conv5_1, filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv5_2') #  14
		conv5_3 = tf.layers.conv2d       (inputs = conv5_2, filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv5_3') #  14
		conv5_4 = tf.layers.conv2d       (inputs = conv5_3, filters = 512, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'conv5_4') #  14
		return pool2, pool3, conv4_4, conv5_4

def SkipFeature(scope, vgg_result, reuse = None):
	"""
		vgg_result: see the return of VGG16 function defined above
	"""
	pool2, pool3, conv4_3, conv5_3 = vgg_result
	with tf.variable_scope(scope, reuse = reuse):
		inter1  = tf.layers.max_pooling2d(inputs = pool2  , pool_size = 2, strides = 2)																	 #  28
		part1   = tf.layers.conv2d       (inputs = inter1 , filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Sconv1' ) #  28
		part2   = tf.layers.conv2d       (inputs = pool3  , filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Sconv2' ) #  28
		part3   = tf.layers.conv2d       (inputs = conv4_3, filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Sconv3' ) #  28
		inter4  = tf.layers.conv2d       (inputs = conv5_3, filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Sconv4' ) #  14
		part4   = tf.image.resize_images (images = inter4 , size = [inter4.shape[1] * 2, inter4.shape[2] * 2])											 #  28
		inter_f = tf.concat([part1, part2, part3, part4], axis = 3)																						 #  28
		feature = tf.layers.conv2d       (inputs = inter_f, filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'SconvF' ) #  28
		return feature

def Mask(scope, feature, reuse = None):
	with tf.variable_scope(scope, reuse = reuse):
		bconv1  = tf.layers.conv2d       (inputs = feature, filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Bconv1' )
		bconv2  = tf.layers.conv2d       (inputs = bconv1 , filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Bconv2' )
		bconv3  = tf.layers.conv2d       (inputs = bconv2 , filters = 512, kernel_size = 1, padding = 'same', activation = tf.nn.relu, name = 'Bconv3' )
		bconv4  = tf.layers.conv2d       (inputs = bconv3 , filters =   2, kernel_size = 1, padding = 'same', activation = None      , name = 'Bconv4' )

		combine = tf.concat([feature, bconv4], -1)

		vconv1  = tf.layers.conv2d       (inputs = combine, filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Vconv1' )
		vconv2  = tf.layers.conv2d       (inputs = vconv1 , filters = 128, kernel_size = 3, padding = 'same', activation = tf.nn.relu, name = 'Vconv2' )
		vconv3  = tf.layers.conv2d       (inputs = vconv2 , filters = 512, kernel_size = 1, padding = 'same', activation = tf.nn.relu, name = 'Vconv3' )
		vconv4  = tf.layers.conv2d       (inputs = vconv3 , filters =   2, kernel_size = 1, padding = 'same', activation = None      , name = 'Vconv4' )

	return bconv4, vconv4

def BottleneckV1(scope, img, out_ch, down, dilation, reuse = None):
	"""
		img   : tensor with shape [batch_size, height, width, num_channels]
		out_ch: number of output channels
		down  : bool
	"""
	assert(out_ch % 4 == 0)
	out_ch_4 = int(out_ch / 4)
	shortcut = (img.get_shape().as_list()[-1] != out_ch)
	stride = 1 + 1 * down
	with tf.variable_scope(scope, reuse = reuse):
		if shortcut:
			sc = tf.layers.conv2d(inputs = img   , filters = out_ch  , kernel_size = 1, padding = 'same', use_bias = False, strides = stride)
			sc = tf.layers.batch_normalization(sc)
		else:
			sc = img
		conv_1 = tf.layers.conv2d(inputs = img   , filters = out_ch_4, kernel_size = 1, padding = 'same', use_bias = False, strides = 1)
		conv_1 = tf.nn.relu(tf.layers.batch_normalization(conv_1))
		conv_2 = tf.layers.conv2d(inputs = conv_1, filters = out_ch_4, kernel_size = 3, padding = 'same', use_bias = False, strides = stride, dilation_rate = dilation)
		conv_2 = tf.nn.relu(tf.layers.batch_normalization(conv_2))
		conv_3 = tf.layers.conv2d(inputs = conv_2, filters = out_ch  , kernel_size = 1, padding = 'same', use_bias = False, strides = 1)
		conv_3 = tf.layers.batch_normalization(conv_3)
	return tf.nn.relu(conv_3 + sc)

def ResNetV1(scope, img, li_nb, reuse = None):
	"""
		img: tensor with shape [batch_size, height, width, num_channels]
		li_nb: list of numbers of bottlenecks for each of the 4 blocks
	"""
	assert(type(li_nb) == list and len(li_nb) == 4)	
	with tf.variable_scope(scope, reuse = reuse):
		with tf.variable_scope('Conv1_1', reuse = reuse):
			conv1 = tf.layers.conv2d(inputs = img, filters =  64, kernel_size = 7, strides = 2, padding = 'same', use_bias = False)
			conv1 = tf.nn.relu(tf.layers.batch_normalization(conv1))		
		conv2 = tf.layers.max_pooling2d(inputs = conv1, pool_size = 3, strides = 2, padding = 'same')
		for i in range(li_nb[0]):
			conv2 = BottleneckV1('Conv2_%d' % (i + 1), conv2, 256 , False, 1, reuse) 
		conv3 = conv2
		for i in range(li_nb[1]):
			conv3 = BottleneckV1('Conv3_%d' % (i + 1), conv3, 512 , i == 0, 1, reuse)
		conv4 = conv3
		for i in range(li_nb[2]):
			conv4 = BottleneckV1('Conv4_%d' % (i + 1), conv4, 1024, False, 2, reuse)
		conv5 = conv4
		for i in range(li_nb[3]):
			conv5 = BottleneckV1('Conv5_%d' % (i + 1), conv5, 2048, False, 4, reuse)
	return conv1, conv2, conv3, conv4, conv5

def ResNetV1_50(scope, img, reuse = None):
	return ResNetV1(scope, img, [3, 4,  6, 3], reuse)

def ResNetV1_101(scope, img, reuse = None):
	return ResNetV1(scope, img, [3, 4, 23, 3], reuse)

def ResNetV1_152(scope, img, reuse = None):
	return ResNetV1(scope, img, [3, 8, 36, 3], reuse)

def SkipFeatureResNet(scope, resnet_result, reuse = None):
	def step(scope, img, out_ch, upsample, reuse = None):
		with tf.variable_scope(scope, reuse = reuse):
			out = tf.layers.conv2d(inputs = img, filters = out_ch, kernel_size = 3, padding = 'same', use_bias = False, strides = 1)
			out = tf.nn.relu(tf.layers.batch_normalization(out))
			if upsample > 1:
				out = tf.image.resize_images(images = out, size = [out.shape[1] * upsample, out.shape[2] * upsample])
		return out

	conv1, conv2, conv3, conv4, conv5 = resnet_result
	with tf.variable_scope(scope, reuse = reuse):
		f1 = step('F1', conv1, 64, 1, reuse)
		f2 = step('F2', conv2, 64, 2, reuse)
		f3 = step('F3', conv3, 64, 4, reuse)
		f4 = step('F4', conv4, 64, 4, reuse)
		f5 = step('F5', conv5, 64, 4, reuse)
		conv_f = tf.concat([f1, f2, f3, f4, f5], axis = 3)
		conv_f = tf.layers.conv2d(inputs = conv_f, filters = 128, kernel_size = 3, padding = 'same', use_bias = False, strides = 2)
		conv_f = tf.layers.batch_normalization(conv_f)
		conv_f = tf.layers.conv2d(inputs = conv_f, filters = 128, kernel_size = 3, padding = 'same', use_bias = False, strides = 2)
		conv_f = tf.layers.batch_normalization(conv_f)
		conv_f = tf.layers.conv2d(inputs = conv_f, filters = 128, kernel_size = 3, padding = 'same', use_bias = False)
		conv_f = tf.layers.batch_normalization(conv_f)
		return conv_f

if __name__ == '__main__':
	img = tf.placeholder(tf.float32, [4, 224, 224, 3])
	resnet_res = ResNetV1_50('ResNetV1_50', img)
	resnet_res1 = ResNetV1_50('ResNetV1_50', img, True)
	skipFeat = SkipFeatureResNet('SkipFeatureResNet', resnet_res)
	skipFeat1 = SkipFeatureResNet('SkipFeatureResNet', resnet_res1, True)
	print(skipFeat.shape)
	# for v in tf.global_variables():
	# 	print(v.name)





