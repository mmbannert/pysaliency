from __future__ import absolute_import, print_function, division

import unittest
import os.path
import dill
import pickle
import pytest

import numpy as np
from imageio import imwrite

import pysaliency
from pysaliency.datasets import FixationTrains, Fixations
from test_helpers import TestWithData


def compare_fixations_subset(f1, f2, f2_inds):
    np.testing.assert_allclose(f1.x, f2.x[f2_inds])
    np.testing.assert_allclose(f1.y, f2.y[f2_inds])
    np.testing.assert_allclose(f1.t, f2.t[f2_inds])
    np.testing.assert_allclose(f1.n, f2.n[f2_inds])
    np.testing.assert_allclose(f1.subjects, f2.subjects[f2_inds])

    assert f1.__attributes__ == f2.__attributes__
    for attribute in f1.__attributes__:
        if attribute == 'scanpath_index':
            continue
        np.testing.assert_array_equal(getattr(f1, attribute), getattr(f2, attribute)[f2_inds])


def compare_fixations(f1, f2, crop_length=False):
    if crop_length:
        maximum_length = np.max(f2.lengths)
    else:
        maximum_length = max(np.max(f1.lengths), np.max(f2.lengths))
    np.testing.assert_array_equal(f1.x, f2.x)
    np.testing.assert_array_equal(f1.y, f2.y)
    np.testing.assert_array_equal(f1.t, f2.t)
    np.testing.assert_array_equal(f1.x_hist[:, :maximum_length], f2.x_hist)
    np.testing.assert_array_equal(f1.y_hist[:, :maximum_length], f2.y_hist)
    np.testing.assert_array_equal(f1.t_hist[:, :maximum_length], f2.t_hist)
    
    assert f1.__attributes__ == f2.__attributes__
    for attribute in f1.__attributes__:
        if attribute == 'scanpath_index':
            continue
        np.testing.assert_array_equal(getattr(f1, attribute), getattr(f2, attribute))



class TestFixations(TestWithData):
    def test_from_fixations(self):
        xs_trains = [
            [0, 1, 2],
            [2, 2],
            [1, 5, 3]]
        ys_trains = [
            [10, 11, 12],
            [12, 12],
            [21, 25, 33]]
        ts_trains = [
            [0, 200, 600],
            [100, 400],
            [50, 500, 900]]
        ns = [0, 0, 1]
        subjects = [0, 1, 1]
        tasks = [0, 1, 0]
        some_attribute = np.arange(len(sum(xs_trains, [])))
        # Create Fixations
        f = pysaliency.FixationTrains.from_fixation_trains(
            xs_trains,
            ys_trains,
            ts_trains,
            ns,
            subjects,
            attributes={'some_attribute': some_attribute},
            scanpath_attributes={'task': tasks},
        )

        # Test fixation trains
        np.testing.assert_allclose(f.train_xs, [[0, 1, 2], [2, 2, np.nan], [1, 5, 3]])
        np.testing.assert_allclose(f.train_ys, [[10, 11, 12], [12, 12, np.nan], [21, 25, 33]])
        np.testing.assert_allclose(f.train_ts, [[0, 200, 600], [100, 400, np.nan], [50, 500, 900]])
        np.testing.assert_allclose(f.train_ns, [0, 0, 1])
        np.testing.assert_allclose(f.train_subjects, [0, 1, 1])

        # Test conditional fixations
        np.testing.assert_allclose(f.x, [0, 1, 2, 2, 2, 1, 5, 3])
        np.testing.assert_allclose(f.y, [10, 11, 12, 12, 12, 21, 25, 33])
        np.testing.assert_allclose(f.t, [0, 200, 600, 100, 400, 50, 500, 900])
        np.testing.assert_allclose(f.n, [0, 0, 0, 0, 0, 1, 1, 1])
        np.testing.assert_allclose(f.subjects, [0, 0, 0, 1, 1, 1, 1, 1])
        np.testing.assert_allclose(f.lengths, [0, 1, 2, 0, 1, 0, 1, 2])
        np.testing.assert_allclose(f.x_hist, [[np.nan, np.nan],
                                              [0, np.nan],
                                              [0, 1],
                                              [np.nan, np.nan],
                                              [2, np.nan],
                                              [np.nan, np.nan],
                                              [1, np.nan],
                                              [1, 5]])

    def test_filter(self):
        xs_trains = []
        ys_trains = []
        ts_trains = []
        ns = []
        subjects = []
        for n in range(1000):
            size = np.random.randint(10)
            xs_trains.append(np.random.randn(size))
            ys_trains.append(np.random.randn(size))
            ts_trains.append(np.cumsum(np.square(np.random.randn(size))))
            ns.append(np.random.randint(20))
            subjects.append(np.random.randint(20))
        f = pysaliency.FixationTrains.from_fixation_trains(xs_trains, ys_trains, ts_trains, ns, subjects)
        # First order filtering
        inds = f.n == 10
        _f = f.filter(inds)
        self.assertNotIsInstance(_f, pysaliency.FixationTrains)
        compare_fixations_subset(_f, f, inds)

        # second order filtering
        inds = np.nonzero(f.n == 10)[0]
        _f = f.filter(inds)
        inds2 = np.nonzero(_f.subjects == 0)[0]
        __f = _f.filter(inds2)
        cum_inds = inds[inds2]
        compare_fixations_subset(__f, f, cum_inds)

    def test_filter_trains(self):
        xs_trains = []
        ys_trains = []
        ts_trains = []
        ns = []
        subjects = []
        for n in range(1000):
            size = np.random.randint(10)
            xs_trains.append(np.random.randn(size))
            ys_trains.append(np.random.randn(size))
            ts_trains.append(np.cumsum(np.square(np.random.randn(size))))
            ns.append(np.random.randint(20))
            subjects.append(np.random.randint(20))

        f = pysaliency.FixationTrains.from_fixation_trains(xs_trains, ys_trains, ts_trains, ns, subjects)
        # First order filtering
        inds = f.train_ns == 10
        _f = f.filter_fixation_trains(inds)
        self.assertIsInstance(_f, pysaliency.FixationTrains)
        equivalent_indices = f.n == 10
        compare_fixations_subset(_f, f, equivalent_indices)

        ## second order filtering
        # inds = np.nonzero(f.n == 10)[0]
        # _f = f.filter(inds)
        # inds2 = np.nonzero(_f.subjects == 0)[0]
        # __f = _f.filter(inds2)
        # cum_inds = inds[inds2]
        # compare_fixations_subset(__f, f, cum_inds)

    def test_save_and_load(self):
        xs_trains = [
            [0, 1, 2],
            [2, 2],
            [1, 5, 3]]
        ys_trains = [
            [10, 11, 12],
            [12, 12],
            [21, 25, 33]]
        ts_trains = [
            [0, 200, 600],
            [100, 400],
            [50, 500, 900]]
        ns = [0, 0, 1]
        subjects = [0, 1, 1]
        # Create /Fixations
        f = pysaliency.FixationTrains.from_fixation_trains(xs_trains, ys_trains, ts_trains, ns, subjects)

        filename = os.path.join(self.data_path, 'fixation.pydat')
        with open(filename, 'wb') as out_file:
            pickle.dump(f, out_file)

        with open(filename, 'rb') as in_file:
            f = pickle.load(in_file)
        # Test fixation trains
        np.testing.assert_allclose(f.train_xs, [[0, 1, 2], [2, 2, np.nan], [1, 5, 3]])
        np.testing.assert_allclose(f.train_ys, [[10, 11, 12], [12, 12, np.nan], [21, 25, 33]])
        np.testing.assert_allclose(f.train_ts, [[0, 200, 600], [100, 400, np.nan], [50, 500, 900]])
        np.testing.assert_allclose(f.train_ns, [0, 0, 1])
        np.testing.assert_allclose(f.train_subjects, [0, 1, 1])

        # Test conditional fixations
        np.testing.assert_allclose(f.x, [0, 1, 2, 2, 2, 1, 5, 3])
        np.testing.assert_allclose(f.y, [10, 11, 12, 12, 12, 21, 25, 33])
        np.testing.assert_allclose(f.t, [0, 200, 600, 100, 400, 50, 500, 900])
        np.testing.assert_allclose(f.n, [0, 0, 0, 0, 0, 1, 1, 1])
        np.testing.assert_allclose(f.subjects, [0, 0, 0, 1, 1, 1, 1, 1])
        np.testing.assert_allclose(f.lengths, [0, 1, 2, 0, 1, 0, 1, 2])
        np.testing.assert_allclose(f.x_hist, [[np.nan, np.nan],
                                              [0, np.nan],
                                              [0, 1],
                                              [np.nan, np.nan],
                                              [2, np.nan],
                                              [np.nan, np.nan],
                                              [1, np.nan],
                                              [1, 5]])


class TestStimuli(TestWithData):
    def test_stimuli(self):
        img1 = np.random.randn(100, 200, 3)
        img2 = np.random.randn(50, 150)
        stimuli = pysaliency.Stimuli([img1, img2])

        self.assertEqual(stimuli.stimuli, [img1, img2])
        self.assertEqual(stimuli.shapes, [(100, 200, 3), (50, 150)])
        self.assertEqual(list(stimuli.sizes), [(100, 200), (50, 150)])
        self.assertEqual(stimuli.stimulus_ids[1], pysaliency.datasets.get_image_hash(img2))
        np.testing.assert_allclose(stimuli.stimulus_objects[1].stimulus_data, img2)
        self.assertEqual(stimuli.stimulus_objects[1].stimulus_id, stimuli.stimulus_ids[1])

        new_stimuli = self.pickle_and_reload(stimuli, pickler=dill)
        print(new_stimuli.stimuli)

        self.assertEqual(len(new_stimuli.stimuli), 2)
        for s1, s2 in zip(new_stimuli.stimuli, [img1, img2]):
            np.testing.assert_allclose(s1, s2)
        self.assertEqual(new_stimuli.shapes, [(100, 200, 3), (50, 150)])
        self.assertEqual(list(new_stimuli.sizes), [(100, 200), (50, 150)])
        self.assertEqual(new_stimuli.stimulus_ids[1], pysaliency.datasets.get_image_hash(img2))
        self.assertEqual(new_stimuli.stimulus_objects[1].stimulus_id, stimuli.stimulus_ids[1])

    def test_slicing(self):
        count = 10
        widths = np.random.randint(20, 200, size=count)
        heights = np.random.randint(20, 200, size=count)
        images = [np.random.randn(h, w, 3) for h, w in zip(heights, widths)]

        stimuli = pysaliency.Stimuli(images)
        for i in range(count):
            s = stimuli[i]
            np.testing.assert_allclose(s.stimulus_data, stimuli.stimuli[i])
            self.assertEqual(s.stimulus_id, stimuli.stimulus_ids[i])
            self.assertEqual(s.shape, stimuli.shapes[i])
            self.assertEqual(s.size, stimuli.sizes[i])

        indices = [2, 4, 7]
        ss = stimuli[indices]
        for k, i in enumerate(indices):
            np.testing.assert_allclose(ss.stimuli[k], stimuli.stimuli[i])
            self.assertEqual(ss.stimulus_ids[k], stimuli.stimulus_ids[i])
            self.assertEqual(ss.shapes[k], stimuli.shapes[i])
            self.assertEqual(ss.sizes[k], stimuli.sizes[i])

        slc = slice(2, 8, 3)
        ss = stimuli[slc]
        indices = range(len(stimuli))[slc]
        for k, i in enumerate(indices):
            np.testing.assert_allclose(ss.stimuli[k], stimuli.stimuli[i])
            self.assertEqual(ss.stimulus_ids[k], stimuli.stimulus_ids[i])
            self.assertEqual(ss.shapes[k], stimuli.shapes[i])
            self.assertEqual(ss.sizes[k], stimuli.sizes[i])


class TestFileStimuli(TestWithData):
    def test_file_stimuli(self):
        img1 = np.random.randint(255, size=(100, 200, 3)).astype('uint8')
        filename1 = os.path.join(self.data_path, 'img1.png')
        imwrite(filename1, img1)

        img2 = np.random.randint(255, size=(50, 150)).astype('uint8')
        filename2 = os.path.join(self.data_path, 'img2.png')
        imwrite(filename2, img2)

        stimuli = pysaliency.FileStimuli([filename1, filename2])

        self.assertEqual(len(stimuli.stimuli), 2)
        for s1, s2 in zip(stimuli.stimuli, [img1, img2]):
            np.testing.assert_allclose(s1, s2)
        self.assertEqual(stimuli.shapes, [(100, 200, 3), (50, 150)])
        self.assertEqual(list(stimuli.sizes), [(100, 200), (50, 150)])
        self.assertEqual(stimuli.stimulus_ids[1], pysaliency.datasets.get_image_hash(img2))
        self.assertEqual(stimuli.stimulus_objects[1].stimulus_id, stimuli.stimulus_ids[1])

        new_stimuli = self.pickle_and_reload(stimuli, pickler=dill)
        print(new_stimuli.stimuli)

        self.assertEqual(len(new_stimuli.stimuli), 2)
        for s1, s2 in zip(new_stimuli.stimuli, [img1, img2]):
            np.testing.assert_allclose(s1, s2)
        self.assertEqual(new_stimuli.shapes, [(100, 200, 3), (50, 150)])
        self.assertEqual(list(new_stimuli.sizes), [(100, 200), (50, 150)])
        self.assertEqual(new_stimuli.stimulus_ids[1], pysaliency.datasets.get_image_hash(img2))
        self.assertEqual(new_stimuli.stimulus_objects[1].stimulus_id, stimuli.stimulus_ids[1])

    def test_slicing(self):
        count = 10
        widths = np.random.randint(20, 200, size=count)
        heights = np.random.randint(20, 200, size=count)
        images = [np.random.randint(255, size=(h, w, 3)) for h, w in zip(heights, widths)]
        filenames = []
        for i, img in enumerate(images):
            filename = os.path.join(self.data_path, 'img{}.png'.format(i))
            imwrite(filename, img)
            filenames.append(filename)

        stimuli = pysaliency.FileStimuli(filenames)
        for i in range(count):
            s = stimuli[i]
            np.testing.assert_allclose(s.stimulus_data, stimuli.stimuli[i])
            self.assertEqual(s.stimulus_id, stimuli.stimulus_ids[i])
            self.assertEqual(s.shape, stimuli.shapes[i])
            self.assertEqual(s.size, stimuli.sizes[i])

        indices = [2, 4, 7]
        ss = stimuli[indices]
        for k, i in enumerate(indices):
            np.testing.assert_allclose(ss.stimuli[k], stimuli.stimuli[i])
            self.assertEqual(ss.stimulus_ids[k], stimuli.stimulus_ids[i])
            self.assertEqual(ss.shapes[k], stimuli.shapes[i])
            self.assertEqual(list(ss.sizes[k]), list(stimuli.sizes[i]))

        slc = slice(2, 8, 3)
        ss = stimuli[slc]
        indices = range(len(stimuli))[slc]
        for k, i in enumerate(indices):
            np.testing.assert_allclose(ss.stimuli[k], stimuli.stimuli[i])
            self.assertEqual(ss.stimulus_ids[k], stimuli.stimulus_ids[i])
            self.assertEqual(ss.shapes[k], stimuli.shapes[i])
            self.assertEqual(list(ss.sizes[k]), list(stimuli.sizes[i]))


@pytest.fixture
def fixation_trains():
    xs_trains = [
        [0, 1, 2],
        [2, 2],
        [1, 5, 3]]
    ys_trains = [
        [10, 11, 12],
        [12, 12],
        [21, 25, 33]]
    ts_trains = [
        [0, 200, 600],
        [100, 400],
        [50, 500, 900]]
    ns = [0, 0, 1]
    subjects = [0, 1, 1]
    tasks = [0, 1, 0]
    some_attribute = np.arange(len(sum(xs_trains, [])))
    return pysaliency.FixationTrains.from_fixation_trains(
        xs_trains,
        ys_trains,
        ts_trains,
        ns,
        subjects,
        attributes={'some_attribute': some_attribute},
        scanpath_attributes={'task': tasks},
    )


@pytest.mark.parametrize('scanpath_indices,fixation_indices', [
    ([0, 2], [0, 1, 2, 5, 6, 7]),
    ([1, 2], [3, 4, 5, 6, 7]),
    ([2], [5, 6, 7]),
])
def test_filter_fixation_trains(fixation_trains, scanpath_indices, fixation_indices):
    sub_fixations = fixation_trains.filter_fixation_trains(scanpath_indices)

    np.testing.assert_array_equal(
        sub_fixations.train_xs,
        fixation_trains.train_xs[scanpath_indices]
    )
    np.testing.assert_array_equal(
        sub_fixations.train_ys,
        fixation_trains.train_ys[scanpath_indices]
    )
    np.testing.assert_array_equal(
        sub_fixations.train_ts,
        fixation_trains.train_ts[scanpath_indices]
    )
    np.testing.assert_array_equal(
        sub_fixations.train_ns,
        fixation_trains.train_ns[scanpath_indices]
    )
    np.testing.assert_array_equal(
        sub_fixations.some_attribute,
        fixation_trains.some_attribute[fixation_indices]
    )
    np.testing.assert_array_equal(
        sub_fixations.scanpath_attributes['task'],
        fixation_trains.scanpath_attributes['task'][scanpath_indices]
    )


def test_read_hdf5_caching(fixation_trains, tmp_path):
    filename = tmp_path / 'fixations.hdf5'
    fixation_trains.to_hdf5(str(filename))

    new_fixations = pysaliency.read_hdf5(str(filename))

    assert new_fixations is not fixation_trains

    new_fixations2 = pysaliency.read_hdf5(str(filename))
    assert new_fixations2 is new_fixations, "objects should not be read into memory multiple times"


def test_fixation_trains_copy(fixation_trains):
    copied_fixation_trains = fixation_trains.copy()
    assert isinstance(copied_fixation_trains, FixationTrains)
    compare_fixations(fixation_trains, copied_fixation_trains)


def test_fixations_copy(fixation_trains):
    fixations = fixation_trains[:-1]
    assert isinstance(fixations, Fixations)
    copied_fixations = fixations.copy()
    assert isinstance(copied_fixations, Fixations)
    compare_fixations(fixations, copied_fixations)


@pytest.fixture
def stimuli_with_attributes():
    stimuli_data = [np.random.randint(0, 255, size=(25, 30, 3)) for i in range(10)]
    attributes = {
        'dva': list(range(10)),
        'other_stuff': np.random.randn(10),
        'some_strings': list('abcdefghij'),
    }
    return pysaliency.Stimuli(stimuli_data, attributes=attributes)


def test_stimuli_attributes(stimuli_with_attributes, tmp_path):
    filename = tmp_path / 'stimuli.hdf5'
    stimuli_with_attributes.to_hdf5(str(filename))

    new_stimuli = pysaliency.read_hdf5(str(filename))

    assert stimuli_with_attributes.attributes.keys() == new_stimuli.attributes.keys()
    np.testing.assert_array_equal(stimuli_with_attributes.attributes['dva'], new_stimuli.attributes['dva'])
    np.testing.assert_array_equal(stimuli_with_attributes.attributes['other_stuff'], new_stimuli.attributes['other_stuff'])
    np.testing.assert_array_equal(stimuli_with_attributes.attributes['some_strings'], new_stimuli.attributes['some_strings'])

    partial_stimuli = stimuli_with_attributes[:5]
    assert stimuli_with_attributes.attributes.keys() == partial_stimuli.attributes.keys()
    assert stimuli_with_attributes.attributes['dva'][:5] == partial_stimuli.attributes['dva']
    assert stimuli_with_attributes.attributes['some_strings'][:5] == partial_stimuli.attributes['some_strings']


@pytest.fixture
def file_stimuli_with_attributes(tmpdir):
    filenames = []
    for i in range(3):
        filename = tmpdir.join('stimulus_{:04d}.png'.format(i))
        imwrite(str(filename), np.random.randint(low=0, high=255, size=(100, 100, 3), dtype=np.uint8))
        filenames.append(str(filename))

    for sub_directory_index in range(3):
        sub_directory = tmpdir.join('sub_directory_{:04d}'.format(sub_directory_index))
        sub_directory.mkdir()
        for i in range(5):
            filename = sub_directory.join('stimulus_{:04d}.png'.format(i))
            imwrite(str(filename), np.random.randint(low=0, high=255, size=(100, 100, 3), dtype=np.uint8))
            filenames.append(str(filename))
    attributes = {
        'dva': list(range(len(filenames))),
        'other_stuff': np.random.randn(len(filenames)),
        'some_strings': list('abcdefghijklmnopqr'),
    }
    return pysaliency.FileStimuli(filenames=filenames, attributes=attributes)


def test_file_stimuli_attributes(file_stimuli_with_attributes, tmp_path):
    filename = tmp_path / 'stimuli.hdf5'
    print(file_stimuli_with_attributes.__attributes__)
    file_stimuli_with_attributes.to_hdf5(str(filename))

    new_stimuli = pysaliency.read_hdf5(str(filename))

    assert file_stimuli_with_attributes.attributes.keys() == new_stimuli.attributes.keys()
    np.testing.assert_array_equal(file_stimuli_with_attributes.attributes['dva'], new_stimuli.attributes['dva'])
    np.testing.assert_array_equal(file_stimuli_with_attributes.attributes['other_stuff'], new_stimuli.attributes['other_stuff'])
    np.testing.assert_array_equal(file_stimuli_with_attributes.attributes['some_strings'], new_stimuli.attributes['some_strings'])

    partial_stimuli = file_stimuli_with_attributes[:5]
    assert file_stimuli_with_attributes.attributes.keys() == partial_stimuli.attributes.keys()
    assert file_stimuli_with_attributes.attributes['dva'][:5] == partial_stimuli.attributes['dva']
    assert file_stimuli_with_attributes.attributes['some_strings'][:5] == partial_stimuli.attributes['some_strings']


def test_concatenate_stimuli_with_attributes(stimuli_with_attributes, file_stimuli_with_attributes):
    concatenated_stimuli = pysaliency.datasets.concatenate_stimuli([stimuli_with_attributes, file_stimuli_with_attributes])

    assert file_stimuli_with_attributes.attributes.keys() == concatenated_stimuli.attributes.keys()
    np.testing.assert_allclose(stimuli_with_attributes.attributes['dva'], concatenated_stimuli.attributes['dva'][:len(stimuli_with_attributes)])
    np.testing.assert_allclose(file_stimuli_with_attributes.attributes['dva'], concatenated_stimuli.attributes['dva'][len(stimuli_with_attributes):])


@pytest.mark.parametrize('stimulus_indices', [[0], [1], [0, 1]])
def test_create_subset_fixation_trains(file_stimuli_with_attributes, fixation_trains, stimulus_indices):
    sub_stimuli, sub_fixations = pysaliency.datasets.create_subset(file_stimuli_with_attributes, fixation_trains, stimulus_indices)

    assert isinstance(sub_fixations, pysaliency.FixationTrains)
    assert len(sub_stimuli) == len(stimulus_indices)
    np.testing.assert_array_equal(sub_fixations.x, fixation_trains.x[np.isin(fixation_trains.n, stimulus_indices)])


@pytest.mark.parametrize('stimulus_indices', [[0], [1], [0, 1]])
def test_create_subset_fixations(file_stimuli_with_attributes, fixation_trains, stimulus_indices):
    # convert to fixations
    fixations = fixation_trains[np.arange(len(fixation_trains))]
    sub_stimuli, sub_fixations = pysaliency.datasets.create_subset(file_stimuli_with_attributes, fixations, stimulus_indices)

    assert not isinstance(sub_fixations, pysaliency.FixationTrains)
    assert len(sub_stimuli) == len(stimulus_indices)
    np.testing.assert_array_equal(sub_fixations.x, fixations.x[np.isin(fixations.n, stimulus_indices)])


if __name__ == '__main__':
    unittest.main()
