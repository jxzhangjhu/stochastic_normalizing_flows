import torch
import numpy as np

from bgtorch.utils.types import assert_numpy


class LossReporter:
    """
        Simple reporter use for reporting losses and plotting them.
    """

    def __init__(self, *labels):
        self._labels = labels
        self._n_reported = len(labels)
        self._raw = [[] for _ in range(self._n_reported)]

    def report(self, *losses):
        assert len(losses) == self._n_reported
        for i in range(self._n_reported):
            self._raw[i].append(assert_numpy(losses[i]))

    def print(self, *losses):
        iter = len(self._raw[0])
        report_str = '{0}\t'.format(iter)
        for i in range(self._n_reported):
            report_str += "{0}: {1:.4f}\t".format(self._labels[i], self._raw[i][-1])
        print(report_str)

    def losses(self, n_smooth=1):
        x = np.arange(n_smooth, len(self._raw[0])+1)
        ys = []
        for (label, raw) in zip(self._labels, self._raw):
            raw = assert_numpy(raw).reshape(-1)
            kernel = np.ones(shape=(n_smooth,)) / n_smooth
            ys.append(np.convolve(raw, kernel, mode="valid"))
        return self._labels, x, ys

    def recent(self, n_recent=1):
        return np.array([raw[-n_recent:] for raw in self._raw])


class KLTrainer(object):

    def __init__(self, bg, optim=None, train_likelihood=True, train_energy=True):
        """ Trainer for minimizing the forward or reverse

        Trains in either of two modes, or a mixture of them:
        1. Forward KL divergence / energy based training. Minimize KL divergence between
           generation probability of flow and target distribution
        2. Reverse KL divergence / maximum likelihood training. Minimize reverse KL divergence between
           data mapped back to latent space and prior distribution.

        """
        self.bg = bg

        if optim is None:
            optim = torch.optim.Adam(bg.parameters(), lr=5e-3)
        self.optim = optim

        loss_names = []
        self.train_likelihood = train_likelihood
        self.w_likelihood = 0.0
        self.train_energy = train_energy
        self.w_energy = 0.0
        if train_likelihood:
            loss_names.append("NLL")
            self.w_likelihood = 1.0
        if train_energy:
            loss_names.append("KLL")
            self.w_energy = 1.0
        self.reporter = LossReporter(*loss_names)


    def train(self, n_iter, data=None, batchsize=128, w_likelihood=None, w_energy=None, n_print=0):
        if w_likelihood is None:
            w_likelihood = self.w_likelihood
        if w_energy is None:
            w_energy = self.w_energy

        for iter in range(n_iter):
            self.optim.zero_grad()
            reports = []

            if self.train_likelihood:
                N = data.shape[0]
                idxs = np.random.choice(N, size=batchsize, replace=True)
                batch = data[idxs]

                # negative log-likelihood of the batch is equal to the energy of the BG
                nll = self.bg.energy(batch).mean()
                reports.append(nll)
                # aggregate weighted gradient
                if w_likelihood > 0:
                    l = w_likelihood / (w_likelihood + w_energy)
                    (l * nll).backward(retain_graph=True)
            if self.train_energy:
                # kl divergence to the target
                kll = self.bg.kldiv(batchsize).mean()
                reports.append(kll)
                # aggregate weighted gradient
                if w_energy > 0:
                    l = w_energy / (w_likelihood + w_energy)
                    (l * kll).backward(retain_graph=True)

            self.reporter.report(*reports)
            if n_print > 0:
                if iter % n_print == 0:
                    self.reporter.print(*reports)

            self.optim.step()

    def losses(self, n_smooth=1):
        return self.reporter.losses(n_smooth=n_smooth)
