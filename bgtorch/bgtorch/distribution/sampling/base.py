import torch


class Sampler(torch.nn.Module):
    
    def __init__(self):
        super().__init__()
    
    def _sample_with_temperature(self, n_samples, temperature):
        raise NotImplementedError()
        
    def _sample(self, n_samples):
        raise NotImplementedError()
    
    def sample(self, n_samples, temperature=None):
        if temperature is not None:
            return self._sample_with_temperature(n_samples, temperature)
        else:
            return self._sample(n_samples)