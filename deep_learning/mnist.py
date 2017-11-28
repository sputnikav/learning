import random

import mnist_loader
import numpy as np
import logging
from pprint import pprint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

TRACE_LEVEL = 5
from cost import *


class Layer:
    def forward(self, inp_array):
        raise NotImplementedError("forward of abstract class not implemented")

    def backprop(self, inp_array, delta_array):
        raise NotImplementedError('backprop of abstract class not implemented')

    def update(self, gradient_w_array, gradient_b_array, learning_rate):
        raise NotImplementedError('backprop of abstract class not implemented')


class ConvoLayer(Layer):
    def __init__(self, filter_size=3, fn_activation=sigmoid, fn_derive=sigmoid_prime, stride=1, pool_size=2):
        self.filter_size = filter_size
        self.weight_array = np.random.normal(size=(filter_size, filter_size))
        # self.bias = np.random.normal()
        self.bias = 0
        self.fn_activation = fn_activation
        self.fn_derive = fn_derive
        self.stride = stride
        self.pool_size = pool_size

    def forward_helper(self, inp):
        """
        :param inp:
        :return:
        """
        trace('input array shape %s', inp.shape.__str__())
        input_size = int(np.sqrt(inp.size))
        # print('input_size', input_size)
        inp_array = inp.reshape(input_size, input_size)
        output_size = input_size - self.filter_size + 1
        output = np.zeros([output_size, output_size])
        weight_len = self.filter_size * self.filter_size
        weight = self.weight_array.reshape([1, weight_len])
        for i in range(0, output_size, self.stride):
            for j in range(0, output_size, self.stride):
                output[i][j] = np.dot(weight,
                                      inp_array[i:i + self.filter_size][:, j:j + self.filter_size].reshape(
                                          [weight_len, 1])) + \
                               self.bias
        return self.fn_activation(output)

    def max_pooling(self, inp):
        output_size = inp.shape[0] / self.pool_size
        output = np.zeros([output_size, output_size])
        for i in range(output_size):
            for j in range(output_size):
                output[i][j] = np.max(
                    inp[i * self.pool_size:(i + 1) * self.pool_size][:, j * self.pool_size:(j + 1) * self.pool_size])
        return output

    def forward(self, inp):
        output = self.forward_helper(inp)
        return self.max_pooling(output)

    def get_max_position(self, activation_array):
        array_size = activation_array.shape[0]
        if array_size % self.pool_size != 0:
            raise NotImplementedError("Array size needs to be even")

        output_size = array_size / 2
        # initialize a dummy array of max position
        max_position_list = []
        for i in range(array_size):
            max_position_list.append([(j, j) for j in range(array_size)])
        # print(max_position_list)

        for i in range(array_size):
            for j in range(array_size):
                matrix = activation_array[
                         i / self.pool_size * self.pool_size:(i / self.pool_size + 1) * self.pool_size][:,
                         j / self.pool_size * self.pool_size:(j / self.pool_size + 1) * self.pool_size]

                row, col = np.unravel_index(matrix.argmax(), matrix.shape)
                max_position_list[i][j] = (
                    row + i / self.pool_size * self.pool_size, col + j / self.pool_size * self.pool_size)
        return max_position_list

    def update(self, gradient_w_array, gradient_b, learning_rate):
        # logger.info('weight array %s' % str(self.weight_array))
        # info('gradient weight array {}', gradient_w_array)
        self.weight_array -= learning_rate * gradient_w_array.reshape(self.weight_array.shape)
        # info('updated weight array {}', self.weight_array)
        # info('gradient bias {}', gradient_b)
        # self.bias -= learning_rate * gradient_b
        # info('updated bias {}', self.bias)

    def backprop(self, inp, delta_array):
        """
        delta_array is a (input_array_size - filter_size + 1)^2/4 x 1. It should be the result of reshaping the max-pooled
        output matrix
        :return:
        delta_array_last: a input_array_size x input_array_size
        """
        # if column array, then reshape
        logger.debug('input array shape %s' % inp.shape.__str__())
        input_array = inp
        if inp.shape[1] == 1:
            logger.debug('input is a column array, needs reshape')
            input_size = int(np.sqrt(inp.shape[0]))
            if input_size ** 2 != inp.shape[0]:
                raise NotImplementedError('input array can not be reshaped to square matrix')
            input_array = inp.reshape(input_size, input_size)
        logger.debug('delta array shape before possible reshape %s' % delta_array.shape.__str__())
        if delta_array.shape[1] == 1:
            delta_array_size = int(np.sqrt(delta_array.shape[0]))
            if delta_array_size ** 2 != delta_array.shape[0]:
                raise NotImplementedError('delta array can not be reshaped to square matrix')
            delta_array = delta_array.reshape(delta_array_size, delta_array_size)
        logger.debug('delta array shape %s' % delta_array.shape.__str__())
        # assert delta_array_size == self.filter_size, "delta array dimension must match with filter size"
        output_size = input_array.shape[0] - self.filter_size + 1
        input_size = input_array.shape[0]
        logger.debug('output size %s' % output_size)

        # if delta_array_size != int((input_size - self.filter_size + 1) / pool_size):
        #     raise NotImplementedError("Delta size needs to be appropriate with the input size")
        weighted_input = np.zeros([output_size, output_size])
        weight_len = self.filter_size * self.filter_size
        weight = self.weight_array.reshape([1, weight_len])
        for i in range(0, output_size, self.stride):
            for j in range(0, output_size, self.stride):
                weighted_input[i][j] = np.dot(weight,
                                              input_array[i:i + self.filter_size][:, j:j + self.filter_size].reshape(
                                                  [weight_len, 1])) + \
                                       self.bias
        activation = self.fn_activation(weighted_input)
        activation_size = activation.shape[0]
        max_position_array = self.get_max_position(activation)
        weight_gradient_array = np.zeros((self.filter_size, self.filter_size))
        for a in range(self.filter_size):
            for b in range(self.filter_size):
                weight_gradient = 0
                for i in range(activation_size):
                    for j in range(activation_size):
                        # only calculate for the max position element
                        if (i, j) != max_position_array[i][j]:
                            continue
                        x = delta_array[i / self.pool_size][j / self.pool_size] * self.fn_derive(weighted_input[i][j]) * \
                            input_array[i + a][j + b]
                        weight_gradient += x
                weight_gradient_array[a][b] = weight_gradient
        # print('weight gradient array', weight_gradient_array)
        back_delta_array = np.zeros((input_size, input_size))
        # calc backprop from the activation array instead of from the input array
        # this should take care of the index difference problem
        for i in range(activation_size):
            for j in range(activation_size):
                if (i, j) != max_position_array[i][j]:
                    continue
                for a in range(self.filter_size):
                    for b in range(self.filter_size):
                        back_delta_array[i + a][j + b] = delta_array[i / self.pool_size][b / self.pool_size] * \
                                                         self.fn_derive(activation[i][j]) * self.weight_array[a][b]

        back_delta_array = back_delta_array / (input_size * input_size)
        # print('back delta array', back_delta_array)
        # getting average of gradient array
        weight_gradient_array = weight_gradient_array / (self.filter_size * self.filter_size)
        # print('weighted gradient array', weight_gradient_array)
        return weight_gradient_array, 0, back_delta_array


class FullyConnectedLayer(Layer):
    def __init__(self, inp_size, out_size, fn_activation=sigmoid, fn_derive=sigmoid_prime):
        self.inp_size = inp_size
        self.out_size = out_size
        self.fn_activation = fn_activation
        self.fn_derive = fn_derive
        self.weight_array = np.random.normal(size=(out_size, inp_size))
        self.bias_array = np.random.normal(size=(out_size, 1))

    def forward(self, inp):
        input_shape = inp.shape
        inp_size = input_shape[0] * input_shape[1]
        inp_array = inp.reshape(inp_size, 1)
        logger.debug('input size %s' % str(self.inp_size))
        assert inp_array.shape == (self.inp_size, 1), "inp.shape %s != (inp_size, 1) (%s, 1)" \
                                                      % (inp_array.shape, self.inp_size)

        z = np.dot(self.weight_array, inp_array) + self.bias_array
        logger.debug('weighted input shape %s' % str(z.shape))
        a = self.fn_activation(z)
        return a

    def update(self, gradient_w_array, gradient_b_array, learning_rate):
        self.weight_array -= learning_rate * gradient_w_array.reshape(self.weight_array.shape)
        # info('updated weight array {}', self.weight_array)
        self.bias_array -= learning_rate * gradient_b_array.reshape(self.bias_array.shape)
        # info('updated bias array {}', self.bias_array)

    def backprop(self, inp, delta_array):
        if delta_array.shape[1] != 1:
            logger.debug('delta array is not a column array, reshape')
            delta_array = delta_array.reshape(np.size(delta_array), 1)
        logger.debug('weight array shape %s' % self.weight_array.shape.__str__())
        logger.debug('delta array shape %s' % delta_array.shape.__str__())
        logger.debug('input array shape %s', inp.shape.__str__())
        assert delta_array.shape == (self.out_size, 1), \
            'delta array should have correct out size (%s, 1) observed=%s' % (self.out_size, delta_array.shape)

        back_delta_array = np.multiply(np.dot(self.weight_array.transpose(), delta_array), \
                                       self.fn_derive(inp).reshape(self.inp_size, 1))
        gradient_b = delta_array
        gradient_w = np.dot(delta_array, inp.reshape(1, self.inp_size))
        return gradient_w, gradient_b, back_delta_array


class ConvoNetwork:
    def __init__(self, layers, monitor_accuracy=True, cost=QuadraticCost):
        self.layers = layers
        self.monitor_accuracy = monitor_accuracy
        self.cost = cost

    def forward(self, inp):
        layer_input_array = inp
        for layer in self.layers:
            weighted_input_array = layer.forward(layer_input_array)
            trace('weighted output {}', weighted_input_array)
            layer_input_array = layer.fn_activation(weighted_input_array)
        return layer_input_array

    def output_shape(self, inp):
        input_shape = inp.shape
        for layer in self.layers:
            if isinstance(layer, FullyConnectedLayer):
                output_shape = (layer.out_size, 1)
            else:
                input_h = input_shape[0]
                input_w = input_shape[1]
                if input_w == 1:
                    height = input_h
                    input_h = input_w = np.sqrt(height)
                    if input_h * input_w != height:
                        raise NotImplementedError('does not know how to shape the input because it is not square')
                output_w = input_w - layer.filter_size + 1
                output_h = input_h - layer.filter_size + 1
                if output_h % layer.pool_size != 0 or output_w % layer.pool_size != 0:
                    raise NotImplementedError('output height and width must be divisible by pool size')
                output_shape = (output_h, output_w)

            input_shape = output_shape

    def update_mini_batch(self, mini_batch, learning_rate):
        gradient_w_arrays = [np.zeros(layer.weight_array.shape) for layer in self.layers]
        gradient_b_arrays = []
        for layer in self.layers:
            if isinstance(layer, FullyConnectedLayer):
                gradient_b_arrays.append(np.zeros(layer.bias_array.shape))
            else:
                gradient_b_arrays.append(0)

        for x, y in mini_batch:
            gradient_w_list, gradient_b_list = self.backprop(x, y)
            for i in range(len(self.layers)):
                logger.debug('weight array of layer %s, %s' % (i, str(gradient_w_arrays[i].shape)))
                logger.debug('gradient weight array of layer %s, %s' % (i, str(gradient_w_list[i].shape)))
                try:
                    logger.debug('bias array of layer %s, %s' % (i, str(gradient_b_arrays[i].shape)))
                    logger.debug('gradient bias array of layer %s, %s' % (i, str(gradient_b_list[i].shape)))
                except:
                    logger.debug('bias array of layer %s, %s' % (i, str(gradient_b_arrays[i])))
                    logger.debug('gradient bias array of layer %s, %s' % (i, str(gradient_b_list[i])))
            # sum all delta weights and delta biases for each training example
            gradient_b_arrays = [nb + dnb for nb, dnb in zip(gradient_b_arrays, gradient_b_list)]
            gradient_w_arrays = [nw + dnw for nw, dnw in zip(gradient_w_arrays, gradient_w_list)]

        gradient_w_arrays = [w / len(mini_batch) for w in gradient_w_arrays]
        gradient_b_arrays = [b / len(mini_batch) for b in gradient_b_arrays]

        for i, layer in enumerate(self.layers):
            layer.update(gradient_w_arrays[i], gradient_b_arrays[i], learning_rate)

    def sgd(self, training_data, epochs, mini_batch_size, learning_rate, test_data=None):
        n = len(training_data)
        for j in range(epochs):
            logger.info('running epoch {0}'.format(j))
            random.shuffle(training_data)
            mini_batches = [training_data[k:k + mini_batch_size] for k in range(0, n, mini_batch_size)]
            for i, mini_batch in enumerate(mini_batches):
                # logger.info('running on mini batch #{0}'.format(i))
                self.update_mini_batch(mini_batch, learning_rate)

            if test_data:
                # print("Epoch {0}: {1}/{2}".format(j, self.evaluate(test_data), len(test_data)))
                self.evaluate(test_data)
            else:
                logger.info("Epoch {0} complete".format(j))

    def evaluate(self, test_data):
        """Return the number of test inputs for which the neural
        network outputs the correct result. Note that the neural
        network's output is assumed to be the index of whichever
        neuron in the final layer has the highest activation."""
        forward = [np.asarray(self.forward(x) - y) for (x, y) in test_data]
        forward = [x.transpose().dot(x) for x in forward]
        cost = sum(forward)
        info('cost {}', cost)
        return cost
        # info('final results {}', [(self.forward(x), y) for (x, y) in test_data])
        # test_results = [(np.argmax(self.forward(x)), y) for (x, y) in test_data]
        # info('test results {}', str(test_results))
        # return sum(int(x == y) for (x, y) in test_results)


    def backprop(self, inp, out):
        layer_input_array = inp
        layer_input_arrays = []
        weighted_input_array = []
        for i, layer in enumerate(self.layers):
            layer_input_arrays.append(layer_input_array)
            weighted_input_array = layer.forward(layer_input_array)
            logger.debug('activation shape at layer %d = %s' % (i, weighted_input_array.shape))
            layer_input_array = layer.fn_activation(weighted_input_array)
        # final activation
        activation_array = layer_input_array
        logger.debug('output shape %s' % out.shape.__str__())
        logger.debug('activation array shape %s' % activation_array.shape.__str__())
        assert out.shape == activation_array.shape, 'activation array and output should have the same size'
        delta_array = self.cost.delta(weighted_input_array, activation_array, out)
        # gradient w and b for each layers
        gradient_w_arrays = []
        gradient_b_arrays = []
        for i in range(len(self.layers)):
            layer_index = len(self.layers) - i - 1
            logger.debug('backprop on layer index %s' % layer_index)
            layer = self.layers[layer_index]
            layer_input = layer_input_arrays[layer_index]
            gradient_w_array, gradient_b_array, back_delta_array = layer.backprop(layer_input, delta_array)
            gradient_w_arrays = [gradient_w_array] + gradient_w_arrays
            gradient_b_arrays = [gradient_b_array] + gradient_b_arrays
            # layer.update(gradient_w_array, gradient_b_array, self.learning_rate)
            delta_array = back_delta_array
        return gradient_w_arrays, gradient_b_arrays

    def update(self, gradient_w_arrays, gradient_b_arrays):
        for i, layer in enumerate(self.layers):
            self.layers[i].update(gradient_w_arrays[i], gradient_b_arrays[i])


def run_convo_network():
    training_data, validation_data, test_data, training_test_data = mnist_loader.load_data_wrapper()
    print('loaded data', len(training_data))

    network = ConvoNetwork(layers=(
        ConvoLayer(),
        FullyConnectedLayer(inp_size=169, out_size=10),
    ))
    network.sgd(training_data[:300], epochs=30, mini_batch_size=10, learning_rate=1.5e-2,
                test_data=training_data[:30])
    print(network.evaluate(test_data))


if __name__ == '__main__':
    run_convo_network()
