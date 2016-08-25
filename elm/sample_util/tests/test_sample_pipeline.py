import copy

import numpy as np
import pandas as pd
import xarray as xr
from sklearn.decomposition import IncrementalPCA
from elm.config import DEFAULTS, DEFAULT_TRAIN, ConfigParser
import elm.sample_util.sample_pipeline as sample_pipeline
from elm.readers import ElmStore
from elm.pipeline.tests.util import (tmp_dirs_context,
                                     random_elm_store,
                                     BANDS,
                                     GEO,
                                     remove_pipeline_transforms)

BASE = copy.deepcopy(DEFAULTS)



def gen(*args, **kwargs):
    yield from range(5)

def sampler():
    es = random_elm_store(BANDS)
    es.flat.values[:, len(BANDS) // 2:] *= 1e-7
    return es

BASE['data_source'] = {'sample_args_generator': gen,
                       'sample_from_args_func': sampler}


def test_sample_pipeline_feature_selection():
    tag = selection_name = 'variance_selection'
    config = copy.deepcopy(BASE)
    with tmp_dirs_context(tag) as (train_path, predict_path, transform_path, cwd):
        remove_pipeline_transforms(config)
        for idx, action in enumerate(config['pipeline']):
            if 'train' in action or 'predict' in action:
                train_name = action.get('train', action.get('predict'))
                if 'sample_pipeline' in action:
                    action['sample_pipeline'] += [{'feature_selection': selection_name}]
                else:
                    action['sample_pipeline'] = [{'feature_selection': selection_name}]

                config2 = ConfigParser(config=BASE)
                config2.feature_selection[selection_name] = {
                    'selection': 'sklearn.feature_selection:VarianceThreshold',
                    'scoring': None,
                    'choices': BANDS,
                    'kwargs': {'threshold': 0.08,},
                }
                action_data = sample_pipeline.get_sample_pipeline_action_data(config2.train[train_name], config2, action)
                transform_models = None
                for repeats in range(5):
                    s, _, _ = sample_pipeline.run_sample_pipeline(action_data, transform_model=None)
                    assert s.flat.shape[1] < 40
                    assert set(s.flat.band.values) < set(BANDS)


def test_elm_store_to_flat_to_elm_store():
    attrs = {'Height': 2,
             'Width': 5,
             'geo_transform': (-10007554.677, 926.625433055833,
                              0.0, 4447802.078667,
                              0.0, -926.6254330558334)}
    samp_np = np.random.uniform(2,3,4*2*5).reshape(4,2,5)
    samp = xr.Dataset({'sample': xr.DataArray(samp_np,
                    dims=['band', 'y', 'x'], attrs=attrs)}, attrs=attrs)
    flat = sample_pipeline.flatten(samp)
    samp2 = sample_pipeline.inverse_flatten(flat)
    assert np.all(samp.flat.values == samp2.flat.values)
    assert samp2.attrs.get('dropped_points') == 0
    values = samp.flat.values.copy()
    values[:, 0, 2] = np.NaN
    values[:, 1, 3] = np.NaN
    samp.flat.values = values
    flat_smaller = sample_pipeline.flatten(samp)
    assert flat_smaller.flat.values.shape[0] == samp.flat.values.shape[1] * samp.flat.values.shape[2] - 2
    samp2 = sample_pipeline.inverse_flatten(flat_smaller)
    v = samp.flat.values
    v2 = samp2.flat.values
    assert v[np.isnan(v)].size == v2[np.isnan(v2)].size
    v = v[~np.isnan(v)]
    v2 = v2[~np.isnan(v2)]
    assert np.all(v == v2)
