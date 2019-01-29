import tensorflow as tf

def leakyReLU(x, alpha):
    return tf.maximum(alpha*x, x)

# This step need to be heavily revised.
def attention_block(x, i):

    channels = x.get_shape()[-1]
    batch_size = x.get_shape()[0]
    with tf.variable_scope('attention_block_%s' % i):

        # Global value for all pixels, measures how important is the context for each of them.
        gamma = tf.get_variable('gamma', shape=(1),initializer=tf.constant_initializer(0.0))

        f = tf.layers.conv2d(inputs=x, filters=channels//8, kernel_size=(1,1), strides=(1,1), padding='same', kernel_initializer=tf.contrib.layers.xavier_initializer())
        g = tf.layers.conv2d(inputs=x, filters=channels//8, kernel_size=(1,1), strides=(1,1), padding='same', kernel_initializer=tf.contrib.layers.xavier_initializer())
        h = tf.layers.conv2d(inputs=x, filters=channels, kernel_size=(1,1), strides=(1,1), padding='same', kernel_initializer=tf.contrib.layers.xavier_initializer())

        # Flatten f, g, and h per channel.
        f_shape = f.get_shape()
        g_shape = g.get_shape()
        h_shape = h.get_shape()
        f_flat = tf.reshape(f, shape=(batch_size, -1, channels//8))
        g_flat = tf.reshape(g, shape=(batch_size, -1, channels//8))
        h_flat = tf.reshape(h, shape=(batch_size, -1, channels))
        
        s = tf.matmul(f_flat, g_flat, transpose_a=True)
        #TODO: Not sure about the output shape. Need to verify.

        #TODO: Verify this step. Not sure how it is calculating the softmax, per row?
        beta = tf.nn.softmax(s)

        # TODO: Not sure about this one either.
        o = tf.matmul(beta, h_flat)
        o = tf.reshape(o, shape=x.get_shape())
        y = gamma*o + x

    return y

def spectral_normalization(filter, power_iterations):
    # Vector is preserved after each SGD iteration, good performance with power_iter=1 and presenving. 
    # Need to make v trainable, and stop gradient descent to going through this path/variables.
    # Isotropic gaussian. 

    filter_shape = filter.get_shape()
    filter_reshape = tf.reshape(filter, [-1, filter_shape[-1]])
    
    u_shape = (1, filter_shape[-1])
    # If I put trainable = False, I don't need to use tf.stop_gradient()
    u = tf.get_variable('u', shape=u_shape, dtype=tf.float32, initializer=tf.truncated_normal_initializer(), trainable=False)

    u_norm = u
    v_norm = None
    
    for i in range(power_iterations):
        v_iter = tf.matmul(u_norm, tf.transpose(filter_reshape))
        v_norm = tf.math.l2_normalize(x=v_iter, epsilon=1e-12)
        u_iter = tf.matmul(v_norm, filter_reshape)
        u_norm = tf.math.l2_normalize(x=u_iter, epsilon=1e-12)

    # How do I verify this?
    # u_norm = tf.stop_gradient(u_norm)
    # v_norm = tf.stop_gradient(v_norm)

    singular_w = tf.matmul(tf.matmul(v_norm, filter_reshape), tf.transpose(u_norm))
    '''
    tf.assign(ref,  value):
        This operation outputs a Tensor that holds the new value of 'ref' after the value has been assigned. 
        This makes it easier to chain operations that need to use the reset value.
        Do the previous iteration and assign u.

    with g.control_dependencies([a, b, c]):
            `d` and `e` will only run after `a`, `b`, and `c` have executed.

        To keep value of u_nom in u?
    If I put this here, the filter won't be use in here until the normalization is done and the value of u_norm kept in u.
    The kernel of the conv it's a variable it self, with its dependencies.
    '''
    with tf.control_dependencies([u.assign(u_norm)]):
        filter_normalized = filter / singular_w
        filter_normalized = tf.reshape(filter_normalized, filter.get_shape())
    return filter_normalized


def convolutional(inputs, output_channels, filter_size, stride, padding, conv_type, scope, data_format='NHWC', output_shape=None, spectral=False, power_iterations=None):
    with tf.variable_scope('conv_layer_%s' % scope):
        current_shape = inputs.get_shape()
        input_channels = current_shape[3]
        
        # Kernel and bias initilization.
        weight_init = tf.contrib.layers.xavier_initializer()
        filter_shape = (filter_size, filter_size, input_channels, output_channels)    
        if 'transpose'in conv_type or 'upscale' in conv_type:
            filter_shape = (filter_size, filter_size, output_channels, input_channels)    

        filter = tf.get_variable('filter', filter_shape, initializer=weight_init)    
        if spectral:
        	filter = spectral_normalization(filter, power_iterations)
        b = tf.get_variable('bias', [1, 1, 1, output_channels], initializer=tf.constant_initializer(0))
        
        # Type of convolutional operation.
        if conv_type == 'upscale':
            output_shape = [tf.shape(inputs)[0], current_shape[1]*2, current_shape[2]*2, output_channels]
            # Weight filter initializer.
            filter = tf.pad(filter, ([1,1], [1,1], [0,0], [0,0]), mode='CONSTANT')
            filter = tf.add_n([filter[1:,1:], filter[:-1,1:], filter[1:,:-1], filter[:-1,:-1]])
            strides = [1, 2, 2, 1]
            output = tf.nn.conv2d_transpose(value=inputs, filter=filter, output_shape=tf.stack(output_shape), strides=strides, padding=padding, data_format=data_format)
            
        elif conv_type == 'downscale':
            # Weight filter initializer.
            filter = tf.pad(filter, ([1,1], [1,1], [0,0], [0,0]), mode='CONSTANT')
            filter = tf.add_n([filter[1:,1:], filter[:-1,1:], filter[1:,:-1], filter[:-1,:-1]])
            strides = [1, 2, 2, 1]
            output = tf.nn.conv2d(input=inputs, filter=filter, strides=strides, padding=padding, data_format=data_format)
            
        elif conv_type == 'transpose':
            output_shape = [tf.shape(inputs)[0], current_shape[1]*stride, current_shape[2]*stride, output_channels]
            strides = [1, stride, stride, 1]
            output = tf.nn.conv2d_transpose(value=inputs, filter=filter, output_shape=tf.stack(output_shape), strides=strides, padding=padding, data_format=data_format)
        
        elif conv_type == 'convolutional':
            strides = [1, stride, stride, 1]
            output = tf.nn.conv2d(input=inputs, filter=filter, strides=strides, padding=padding, data_format=data_format)
        
        output += b
    return output


def dense(inputs, out_dim, scope, use_bias=True, spectral=False, power_iterations=None):
    with tf.variable_scope('dense_layer_%s' % scope):
        in_dim = inputs.get_shape()[-1]
        weights = tf.get_variable('kernel', shape=[in_dim, out_dim], dtype=tf.float32)
        output = tf.matmul(inputs, spectral_normalization(weights, power_iterations))
        if use_bias : 
            bias = tf.get_variable("bias", [out_dim], initializer=tf.constant_initializer(0.0))
        output += bias
    return output


