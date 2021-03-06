import os
import scipy.optimize
import numpy as np
from pysqoe.models import QoeModel


def fun(coeff, data):
    a, b, c = coeff
    x1, x2, x3, x4 = data.T
    y = x1 - a * x2 - b * x3 - c * x4
    return y

def fun_s(coeff, data):
    b, c = coeff
    x1, _, x3, x4 = data.T
    y = x1 - b * x3 - c * x4
    return y

def fun_a(coeff, data):
    a = coeff
    x1, x2, _, _ = data.T
    y = x1 - a * x2 
    return y

# We use PLCC loss to alleviate the potential mismatch in scales between MOS and prediction
def objective(coeff, data, target, fun):
    prediction = fun(coeff, data)
    yhat = prediction - np.mean(prediction)
    y = target - np.mean(target)
    loss = (-1) * np.inner(y, yhat) / (np.std(y) * np.std(yhat) * y.size)
    return loss

class Spiteri2016QoE(QoeModel):
    r"""
    This is an implementation of the objective QoE model described in [R1].
    Note that we normalize the original QoE model by the number of segment.
    Since the range of log bitrate is very different from mos, we maximize
    linear correlation.

    Input features:
        1. x1: average log bitrate
        2. x2: total variation of log bitrate / (K - 1), where K is the number of segment
        3. x3: average rebuffering duration
        4. x4: initial buffering duration / K, where K is the number of chunks
    Model parameters: a, b, c
    QoE = x1 - a * x2 - b * x3 - c * x4

    [R1]:  K. Spiteri, R. Urgaonkar, and R. K. Sitaraman, ``BOLA: Near-Optimal Bitrate
           Adaptation for Online Videos,'' IEEE Int. Conf. Computer Communications, 
           San Francisco, CA, USA, 1-9.
    """
    def __init__(self):
        model_dir = os.path.dirname(os.path.realpath(__file__))
        self.param_s_file = os.path.join(model_dir, 'param_s.txt')
        self.param_a_file = os.path.join(model_dir, 'param_a.txt')
        self.x_min = 60

        if os.path.isfile(self.param_s_file):
            self.param_s = np.loadtxt(self.param_s_file, ndmin=1)
        else:
            self.param_s = None

        if os.path.isfile(self.param_a_file):
            self.param_a = np.loadtxt(self.param_a_file, ndmin=1)
        else:
            self.param_a = None

    def __call__(self, streaming_video):
        assert self.param_s is not None, 'Model weights do not exist.'
        assert self.param_a is not None, 'Model weights do not exist.'
        coeff = np.concatenate((self.param_a, self.param_s))
        x1, x2, x3, x4 = self._extract(streaming_video)
        data = np.array([x1, x2, x3, x4])
        q = fun(coeff, data)
        return q

    def _extract(self, streaming_video):
        x1_k = np.log(np.array(streaming_video.data['video_bitrate']) / self.x_min)
        x2_k = np.array(streaming_video.data['rebuffering_duration'])
        K = x1_k.size
        x1 = np.sum(x1_k) / K
        x2 = np.sum(np.abs(x1_k[1:] - x1_k[:-1])) / K
        x3 = np.sum(x2_k[1:]) / K
        x4 = x2_k[0] / K
        return x1, x2, x3, x4

    def train(self, dataset_s, dataset_a):
        r"""
        We have also tried to train the parameter of the model jointly on dataset_s + dataset_a,
        but it does not seem to work well.
        """
        print('Training Spiteri2016QoE...')
        self._train_s(dataset=dataset_s)
        self._train_a(dataset=dataset_a)

    def _train_s(self, dataset):
        coeff_0 = np.array([2.66, 2.66])
        data = []
        target = []
        for i in range(len(dataset)):
            streaming_video, mos = dataset[i]
            x1, x2, x3, x4 = self._extract(streaming_video)
            data.append([x1, x2, x3, x4])
            target.append(mos)

        data = np.array(data)
        target = np.array(target)
        general_result = scipy.optimize.minimize(objective, coeff_0,
                                                 method='Nelder-Mead',
                                                 args=(data, target, fun_s))
        coeff = general_result.x
        np.savetxt(self.param_s_file, coeff, fmt='%03.3f')

    def _train_a(self, dataset):
        coeff_0 = np.array([2])
        data = []
        target = []
        for i in range(len(dataset)):
            streaming_video, mos = dataset[i]
            x1, x2, x3, x4 = self._extract(streaming_video)
            data.append([x1, x2, x3, x4])
            target.append(mos)

        data = np.array(data)
        target = np.array(target)
        general_result = scipy.optimize.minimize(objective, coeff_0,
                                                 method='Nelder-Mead',
                                                 args=(data, target, fun_a))
        coeff = general_result.x
        np.savetxt(self.param_a_file, coeff, fmt='%03.3f')

    # def train(self, dataset_s, dataset_a):
    #     print('Training Spiteri2016QoE...')
    #     coeff_0 = np.array([20, 20, 3])
    #     dataset = dataset_s + dataset_s + dataset_s + dataset_a
    #     data = []
    #     target = []
    #     for i in range(len(dataset)):
    #         streaming_video, mos = dataset[i]
    #         x1, x2, x3 = self._extract(streaming_video)
    #         data.append([x1, x2, x3])
    #         target.append(mos)

    #     data = np.array(data)
    #     target = np.array(target)
    #     general_result = scipy.optimize.minimize(objective, coeff_0,
    #                                              method='Nelder-Mead',
    #                                              args=(data, target, fun))
    #     coeff = general_result.x
    #     np.savetxt(self.param_file, coeff, fmt='%03.3f')
