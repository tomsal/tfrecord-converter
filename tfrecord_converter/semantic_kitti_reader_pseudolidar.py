#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SemanticKittiReaderPseudoLidar overloads the read method of SemanticKittiReader
to also read the files generated by PseudoLidar++.
"""
import typing

import numpy as np
from .semantic_kitti_reader import SemanticKittiReader


class SemanticKittiReaderPseudoLidar(SemanticKittiReader):

    def __init__(
        self,
        *args,
        filter_by_elevation_angle: bool = False,
        **kwargs
    ):
        super(SemanticKittiReaderPseudoLidar, self).__init__(*args, **kwargs)
        self.filter_by_elevation_angle = filter_by_elevation_angle
        if self.testset_flag:
            raise NotImplementedError("Test set conversion has not been implemented yet.")

    def filter_by_theta(
            self,
            points,
            bin_width=0.1
    ):
        theta = np.arccos(
                  np.sqrt((points[:,:2]**2).sum(axis=1))
                  / np.sqrt((points[:,:3]**2).sum(axis=1))
                )
        theta_deg = theta/np.pi * 180
        limit_lower = np.arange(0,15,0.4)
        within_limits =\
            np.logical_and(
                np.less_equal(limit_lower[None,:], theta_deg[:,None]),
                np.less(theta_deg[:,None], (limit_lower+bin_width)[None,:]))
        within_limits = within_limits.any(axis=1)
        return within_limits

    def read(
        self,
        sample: typing.Union[
            typing.Tuple[str, int, int, int, int], typing.Tuple[int, int]
        ],
        sample_id: str,
    ):

        if not self.testset_flag:
            kitti_sequence = self.kitti_raw_seq_template.format(
                day=sample[0], seq=sample[1]
            )
            kitti_raw_seq_folder = self.kitti_raw_root / kitti_sequence
            if not kitti_raw_seq_folder.is_dir():
                # use from backup KITTI Odometry location
                # (one sequence is missing in KITTI raw)
                point_cloud_file = (
                    self.kitti_odometry_root
                    / "{:02d}".format(sample[3])
                    / "velodyne"
                    / "{:06d}.bin".format(sample[4])
                )
                pseudo_point_cloud_file = (
                    self.kitti_odometry_root
                    / "{:02d}".format(sample[3])
                    / "pseudolidar"
                    / "{:06d}.bin".format(sample[4])
                )
            else:
                point_cloud_file = (
                    self.kitti_raw_root
                    / kitti_sequence
                    / "velodyne_points"
                    / "data"
                    / "{:010d}.bin".format(sample[2])
                )
                pseudo_point_cloud_file = (
                    self.kitti_raw_root
                    / kitti_sequence
                    / "pseudolidar_points"
                    / "data"
                    / "{:010d}.bin".format(sample[2])
                )
        else:
            point_cloud_file = self._data_cache[sample[0]][sample[1]]
            raise NotImplementedError("Test set conversion has not been implemented yet.")

        point_cloud = self.read_pointcloud(point_cloud_file)
        pseudo_point_cloud = self.read_pointcloud(pseudo_point_cloud_file)
        if self.filter_by_elevation_angle:
            valid_points = self.filter_by_theta(pseudo_point_cloud)
            pseudo_point_cloud = pseudo_point_cloud[valid_points]

        r = {
            "sample_id": sample_id.encode("utf-8"),
            "point_cloud": point_cloud.flatten(),
            "pseudo_point_cloud": pseudo_point_cloud.flatten(),
        }

        if not self.testset_flag:
            label_file = (
                self.semantic_kitti_root
                / "{:02d}".format(sample[3])
                / "labels"
                / "{:06d}.label".format(sample[4])
            )
            label_sem, _ = self.read_label(label_file)
            if label_sem.shape[0] != point_cloud.shape[0]:
                raise RuntimeError(
                    "Length of labels and point cloud does not match"
                    "({} and {})".format(str(point_cloud_file), str(label_file))
                )
            try:
                label_sem = self._label_mapping(label_sem)
            except TypeError:
                raise RuntimeError(
                    "Invalid label entry in label data '{}'.".format(label_file)
                )
            r["semantic_labels"] = label_sem
        return r