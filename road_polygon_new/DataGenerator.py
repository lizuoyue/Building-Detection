import math, random
import numpy as np
from PIL import Image, ImageDraw
import time, json
from scipy.stats import multivariate_normal
from Config import *
from scipy.ndimage.filters import gaussian_filter
import scipy, socket, sys, os
from pycocotools.coco import COCO

config = Config()
SHOW = False

class directed_graph(object):
	def __init__(self, downsample = 8):
		self.v = []
		self.v_org = []
		self.e = []
		self.nb = []
		return

	def add_v(self, v):
		self.v.append(v)
		self.v_org.append((v[0] * 8 + 4, v[1] * 8 + 4))
		self.nb.append([])
		return

	def add_e(self, v1, v2, w = None):
		assert(v1 in range(len(self.v)))
		assert(v2 in range(len(self.v)))
		if w is None:
			w = self.dist(self.v[v1], self.v[v2])
		self.e.append((v1, v2, w))
		self.nb[v1].append((v2, w))
		return

	def dist(self, v1, v2):
		diff = np.array(v1) - np.array(v2)
		return np.sqrt(np.dot(diff, diff))

	def spfa(self, source):
		dist = [1e9 for i in range(len(self.v))]
		prev = [None for i in range(len(self.v))]
		in_q = [False for i in range(len(self.v))]
		dist[source] = 0
		q = [source]
		in_q[source] = True
		while len(q) > 0:
			u = q.pop(0)
			in_q[u] = False
			for v, w in self.nb[u]:
				alt = dist[u] + w
				if alt < dist[v]:
					dist[v] = alt
					prev[v] = u
					if not in_q[v]:
						in_q[v] = True
						q.append(v)
		dist = np.array(dist)
		dist[dist > 1e8] = -1e9
		return dist, prev

	def shortest_path_all(self):
		self.sp = []
		for i in range(len(self.v)):
			self.sp.append(self.spfa(i))
		self.sp_max_idx = [np.argmax(dist) for dist, _ in self.sp]
		self.sp_idx_t = []
		for dist, _ in self.sp:
			self.sp_idx_t.append([idx for idx, d in enumerate(list(dist)) if d > 0.5])
		self.sp_idx_s = [idx for idx, item in enumerate(self.sp_idx_t) if len(item) > 0]
		return

def make_ellipse(p, pad = 10):
	return [(p[0] - pad, p[1] - pad), (p[0] + pad, p[1] + pad)]

def rotate1(w, h, x, y):
	return h, w, y, w - 1 - x

def rotateN(n, w, h, x, y):
	for _ in range(n):
		w, h, x, y = rotate1(w, h, x, y)
	return w, h, x, y

class VertexPool(object):
	def __init__(self, v_out_res):
		self.v_out_res = v_out_res
		self.blank = np.zeros(self.v_out_res, dtype = np.uint8)
		self.vertex_pool = [[] for i in range(self.v_out_res[1])]
		for i in range(self.v_out_res[1]):
			for j in range(self.v_out_res[0]):
				self.vertex_pool[i].append(np.copy(self.blank))
				self.vertex_pool[i][j][i, j] = 255
				self.vertex_pool[i][j] = Image.fromarray(self.vertex_pool[i][j])
		return

vp = VertexPool(config.V_OUT_RES)

class DataGenerator(object):
	def __init__(self, city_name, img_size, v_out_res, max_seq_len, mode = 'train'):
		assert(mode in ['train', 'val', 'test'])
		self.mode = mode
		self.city_name = city_name
		self.img_size = img_size
		self.v_out_res = v_out_res
		self.max_seq_len = max_seq_len

		self.TRAIN_ANNOTATIONS_PATH = config.PATH[city_name]['ann-train']
		self.VAL_ANNOTATIONS_PATH   = config.PATH[city_name]['ann-val']
		self.TEST_ANNOTATIONS_PATH  = config.PATH[city_name]['ann-test']
		self.TRAIN_IMAGES_DIRECTORY = config.PATH[city_name]['img-train']
		self.VAL_IMAGES_DIRECTORY   = config.PATH[city_name]['img-val']
		self.TEST_IMAGES_PATH       = config.PATH[city_name]['img-test']

		self.TEST_CURRENT = 0
		self.TEST_FLAG = True
		self.TEST_RESULT = []

		if self.mode == 'test':
			self.coco_test = COCO(self.TEST_ANNOTATIONS_PATH)
			self.TEST_IMAGES_DIRECTORY = config.PATH[city_name]['img-test']
			self.TEST_IMAGE_IDS = list(self.coco_test.getImgIds(catIds = self.coco_test.getCatIds()))
		if self.mode == 'val':
			self.coco_valid = COCO(self.VAL_ANNOTATIONS_PATH)
			self.TEST_IMAGES_DIRECTORY = config.PATH[city_name]['img-val']
			self.TEST_IMAGE_IDS = list(self.coco_valid.getImgIds(catIds = self.coco_valid.getCatIds()))
		if mode == 'train':
			self.coco_train = COCO(self.TRAIN_ANNOTATIONS_PATH)
			self.coco_valid = COCO(self.VAL_ANNOTATIONS_PATH)
			self.train_img_ids = self.coco_train.getImgIds(catIds = self.coco_train.getCatIds())
			self.train_ann_ids = self.coco_train.getAnnIds(catIds = self.coco_train.getCatIds())
			self.valid_img_ids = self.coco_valid.getImgIds(catIds = self.coco_valid.getCatIds())
			self.valid_ann_ids = self.coco_valid.getAnnIds(catIds = self.coco_valid.getCatIds())

			train_anns = self.coco_train.loadAnns(self.train_ann_ids)
			valid_anns = self.coco_valid.loadAnns(self.valid_ann_ids)

			print('Totally %d patches for train.' % len(self.train_ann_ids))
			print('Totally %d patches for valid.' % len(self.valid_ann_ids))

		# 
		self.blank = Image.fromarray(np.zeros(self.v_out_res, dtype = np.uint8))
		self.vertex_pool = [[] for i in range(self.v_out_res[1])]
		for i in range(self.v_out_res[1]):
			for j in range(self.v_out_res[0]):
				self.vertex_pool[i].append(np.copy(self.blank))
				self.vertex_pool[i][j][i, j] = 255
				self.vertex_pool[i][j] = Image.fromarray(self.vertex_pool[i][j])
		return

	def getSingleArea(self, mode, img_id, seq_id, rotate):
		if self.mode == 'train':
			assert(mode in ['train', 'val'])
		else:
			assert(mode == self.mode)

		# Rotate, anticlockwise
		if self.mode == 'train':
			rotate_deg = rotate * 90
			if mode == 'train':
				img_info = self.coco_train.loadImgs([img_id])[0]
				image_path = os.path.join(self.TRAIN_IMAGES_DIRECTORY, img_info['file_name'])
				annotations = self.coco_train.loadAnns(self.coco_train.getAnnIds(imgIds = img_info['id']))
			if mode == 'val':
				img_info = self.coco_valid.loadImgs([img_id])[0]
				image_path = os.path.join(self.VAL_IMAGES_DIRECTORY, img_info['file_name'])
				annotations = self.coco_valid.loadAnns(self.coco_valid.getAnnIds(imgIds = img_info['id']))
		else:
			if mode == 'val':
				img_info = self.coco_valid.loadImgs([img_id])[0]
			if mode == 'test':
				img_info = self.coco_test.loadImgs([img_id])[0]
			image_path = os.path.join(self.TEST_IMAGES_DIRECTORY, img_info['file_name'])

		img = Image.open(image_path)
		org_w, org_h = img.size
		ret_img = img.rotate(rotate_deg).resize(self.img_size)

		if SHOW:
			ret_img.save('%d_a.png' % img_id)

		ret_img = np.array(ret_img, np.float32)[..., 0: 3]
		if self.mode != 'train':
			return ret_img

		assert(len(annotations) == 1)
		w8, h8 = self.v_out_res
		annotation = annotations[0]

		v_set = set()
		for (x1, y1), (x2, y2) in annotation['segmentation']:
			v_set.add((x1, y1))
			v_set.add((x2, y2))
		v_li = list(v_set)
		v_li.sort()
		v_li_8 = [(round(x / (org_w - 1) * (w8 - 1)), round(y / (org_h - 1) * (h8 - 1))) for x, y in v_li]
		v_li_8 = [rotateN(rotate, w8, h8, x, y)[2:] for x, y in v_li_8]
		v_li_8_unique = list(set(v_li_8))
		v_li_8_unique.sort()
		v_li_8_d = {v: k for k, v in enumerate(v_li_8_unique)}
		d = {v: v_li_8_d[v8] for v, v8 in zip(v_li, v_li_8)}

		edges = [(d[tuple(v1)], d[tuple(v2)]) for v1, v2 in annotation['segmentation']]
		polygons = [[d[tuple(v)] for v in polygon] for polygon in annotation['polygons']]
		for i in range(len(polygons)):
			temp = [polygons[i][0]]
			for j in range(1, len(polygons[i])):
				if polygons[i][j] != temp[-1]:
					temp.append(polygons[i][j])
			polygons[i] = temp

		start_indices = []
		new_polygons = []
		for pid, polygon in enumerate(polygons):
			if len(polygon) < 3:
				continue
			if polygon[0] == polygon[-1]:
				temp = polygon[:-1]
			else:
				temp = polygon
			if len(temp) == 2 and (temp[0] == temp[1]):
				continue
			new_polygon = []
			start_index = []
			for pvid in range(len(temp)):
				if temp[pvid-1] == temp[(pvid+1)%len(temp)]:
					start_index.append(len(new_polygon))
					new_polygon.append(temp[pvid])
				new_polygon.append(temp[pvid])
			new_polygons.append(new_polygon)
			start_indices.append(start_index)
		polygons = new_polygons

		if len(v_li_8_unique) == 1:
			v_li_8_unique = []
			edges = []
			polygons = []

		# Draw boundary and vertices
		boundary = Image.new('P', (w8, h8), color = 0)
		draw = ImageDraw.Draw(boundary)
		for e in edges:
			draw.line(list(v_li_8_unique[e[0]]) + list(v_li_8_unique[e[1]]), fill = 255, width = 1)
		if SHOW:
			boundary.resize(self.img_size).save('%d_b.png' % img_id)
		boundary = np.array(boundary) / 255.0

		vertices = Image.new('P', (w8, h8), color = 0)
		draw = ImageDraw.Draw(vertices)
		for i in range(len(v_li_8_unique)):
			draw.ellipse(make_ellipse(v_li_8_unique[i], pad = 0), fill = 255, outline = 255)
		if SHOW:
			vertices.resize(self.img_size).save('%d_c.png' % img_id)
		vertices = np.array(vertices) / 255.0

		if SHOW:
			print('Img', img_id, len(polygons), 'polygons')

		# RNN in and out
		vertex_inputs = []
		vertex_outputs = []
		ends = []
		seq_lens = []
		for pid, polygon in enumerate(polygons):
			if len(polygon) <= 2:
				if len(polygon) <= 1:
					print('Invalid polygon (%d)' % pid)
					continue
				else:
					if polygon[0] == polygon[1]:
						print('Invalid polygon (%d)' % pid)
						continue

			if len(start_indices[pid]) > 0:
				start = np.random.randint(len(start_indices[pid]))
				start = start_indices[pid][start]
			else:
				start = np.random.randint(len(polygon))

			full_path = polygon[start:] + polygon[:start]
			full_path.append(full_path[0])
			full_path = [v_li_8_unique[idx] for idx in full_path]
			seq_len = len(full_path) - 1

			vertex_input_1 = [self.vertex_pool[r][c] for c, r in full_path[:-1]]
			vertex_input_2 = [self.vertex_pool[r][c] for c, r in full_path[ 1:]]
			vertex_input = [[in1, in2] for in1, in2 in zip(vertex_input_1, vertex_input_2)]
			vertex_output = vertex_input_2[1:]

			while len(vertex_input) < self.max_seq_len:
				vertex_input.append([self.blank, self.blank])
			while len(vertex_output) < self.max_seq_len:
				vertex_output.append(self.blank)

			vertex_input = vertex_input[: self.max_seq_len]
			vertex_output = vertex_output[: self.max_seq_len]

			end = np.zeros([self.max_seq_len])
			if seq_len <= self.max_seq_len:
				end[seq_len - 1] = 1

			if SHOW:
				tp = ['in1', 'in2', 'out']
				for seq, vvv in enumerate([[cao[0] for cao in vertex_input], [cao[1] for cao in vertex_input], vertex_output]):
					for i, item in enumerate(vvv):
						item.save('%d_p%d_%d_%s.png' % (img_id, pid, i, tp[seq]))
				print(end)
				print(seq_len)

			vertex_input = [np.array([np.array(sub) / 255.0 for sub in item]) for item in vertex_input]
			vertex_output = [np.array(item) / 255.0 for item in vertex_output]
			vertex_inputs.append(vertex_input)
			vertex_outputs.append(vertex_output)
			ends.append(end)
			seq_lens.append(min(seq_len, self.max_seq_len))

		seq_idx = seq_id * np.ones([len(ends)], np.int32)
		vertex_inputs = np.array(vertex_inputs)
		if vertex_inputs.shape[0] > 0:
			vertex_inputs = vertex_inputs.transpose([0, 1, 3, 4, 2])
		vertex_outputs = np.array(vertex_outputs)
		ends = np.array(ends)
		seq_lens = np.array(seq_lens)

		if SHOW:
			input()

		# print(ret_img.shape)
		# print(boundary.shape)
		# print(vertices.shape)
		# print(vertex_inputs.shape)
		# print(vertex_outputs.shape)
		# print(ends.shape)
		# print(seq_lens.shape)

		# if vertex_outputs.shape[0] > 0:
		# 	print(np.reshape(vertex_inputs, [-1, self.max_seq_len, 28 * 28, 2]).sum(axis = -2))
		# 	t1 = np.reshape(vertex_outputs, [-1, self.max_seq_len, 28 * 28])
		# 	t2 = ends[..., np.newaxis]
		# 	tt = np.concatenate([t1, t2], axis = -1)
		# 	ttt = tt.sum(axis = -1)
		# 	print(ttt)
		# 	print(seq_lens)
		# 	input()

		return ret_img, boundary, vertices, vertex_inputs, vertex_outputs, ends, seq_lens, seq_idx

	def getAreasBatch(self, batch_size, mode):
		res = []
		rotate = random.choice([0, 1, 2, 3])
		if self.mode == 'train':
			assert(mode in ['train', 'val'])
			while True:
				ids = np.random.choice(self.train_img_ids, batch_size, replace = False)
				print(ids, rotate)
				for i in range(batch_size):
					res.append(self.getSingleArea('train', ids[i], i, rotate))
				new_res = [np.array([item[i] for item in res]) for i in range(3)]
				for i in range(3, 8):
					li = [item[i] for item in res if item[i].shape[0] > 0]
					if li:
						new_res.append(np.concatenate(li, axis = 0))
					else:
						break
				if len(new_res) != 8:
					print('No polygons in the images, re-generate ...')
					res = []
					continue
				assert(new_res[-1].shape[0] > 0)
				choose = np.random.choice(new_res[-1].shape[0], config.TRAIN_NUM_PATH, replace = (new_res[-1].shape[0] < config.TRAIN_NUM_PATH))
				for i in range(3, 8):
					new_res[i] = new_res[i][choose]
				break
			# for item in new_res:
			# 	print(item.shape)
			# input()
			return new_res



def findPeaks(heatmap, sigma = 0, min_val = 0.5):
	th = 0
	hmap = gaussian_filter(heatmap, sigma)
	map_left = np.zeros(hmap.shape)
	map_left[1:,:] = hmap[:-1,:]
	map_right = np.zeros(hmap.shape)
	map_right[:-1,:] = hmap[1:,:]
	map_up = np.zeros(hmap.shape)
	map_up[:,1:] = hmap[:,:-1]
	map_down = np.zeros(hmap.shape)
	map_down[:,:-1] = hmap[:,1:]
	map_ul = np.zeros(hmap.shape)
	map_ul[1:,1:] = hmap[:-1,:-1]
	map_ur = np.zeros(hmap.shape)
	map_ur[:-1,1:] = hmap[1:,:-1]
	map_dl = np.zeros(hmap.shape)
	map_dl[1:,:-1] = hmap[:-1,1:]
	map_dr = np.zeros(hmap.shape)
	map_dr[:-1,:-1] = hmap[1:,1:]
	summary = np.zeros(hmap.shape)
	summary += hmap>=map_left+th
	summary += hmap>=map_right+th
	summary += hmap>=map_up+th
	summary += hmap>=map_down+th
	summary += hmap>=map_dl+th
	summary += hmap>=map_dr+th
	summary += hmap>=map_ul+th
	summary += hmap>=map_ur+th
	peaks_binary = np.logical_and.reduce((summary >= 8, hmap >= min_val))
	peaks = list(zip(np.nonzero(peaks_binary)[1], np.nonzero(peaks_binary)[0])) # note reverse
	peaks_with_score = [x + (float(heatmap[x[1],x[0]]),) for x in peaks]
	return peaks_with_score









def getVE(hmb, hmv):
	assert(hmb.shape == hmv.shape)
	h, w = hmb.shape[0: 2]
	peaks_with_score = findPeaks(hmv, min_val = 0.85)
	peaks_with_score = sorted(peaks_with_score, key = lambda x: x[2], reverse = True)
	num_peaks = len(peaks_with_score)
	nb = [[] for _ in range(num_peaks)]
	score_table = {}
	edges_map = Image.new('P', (w, h), color = 0)
	edges_draw = ImageDraw.Draw(edges_map)
	for i in range(num_peaks):
		x1, y1, _ = peaks_with_score[i]
		for j in range(i + 1, num_peaks):
			x2, y2, _ = peaks_with_score[j]
			edge_map = Image.new('P', (w, h), color = 0)
			edge_draw = ImageDraw.Draw(edge_map)
			edge_draw.line([x1, y1, x2, y2], fill = 255, width = 1)
			edge_map = np.array(edge_map, np.float32)
			score = np.mean(hmb[edge_map > 128])
			score_table[(i, j)] = score
			score_table[(j, i)] = score
			if score > 0.7:
				edges_draw.line([x1, y1, x2, y2], fill = 255, width = 1)
				nb[i].append(j)
				nb[j].append(i)
	edges_map = np.array(edges_map, np.float32) / 255.0

	pairs = []
	v_val2idx = {}
	peaks_map = np.zeros((w, h), np.float32)
	for i in range(num_peaks):
		x1, y1, _ = peaks_with_score[i]
		v_val2idx[(x1, y1)] = i
		if nb[i]:
			peaks_map[y1, x1] = 1
			if x1 in [0, 27] or y1 in [0, 27]:
				pairs.append(
					np.concatenate([
						np.array(vp.vertex_pool[y1][x1])[..., np.newaxis] / 255.0,
						np.array(vp.vertex_pool[y1][x1])[..., np.newaxis] / 255.0
					], axis = -1)
				)
	
	return edges_map, peaks_map, pairs[:5], peaks_with_score, v_val2idx, score_table


def getVESimple(hmb, hmv):
	assert(hmb.shape == hmv.shape)
	h, w = hmb.shape[0: 2]
	peaks_with_score = findPeaks(hmv, min_val = 0.85)
	peaks_with_score = [(x, y, s) for x, y, s in peaks_with_score if True or hmb[y, x] > 0.8]
	peaks_map = np.zeros([w, h], np.float32)
	edges_map = Image.new('P', (w, h), color = 0)
	draw = ImageDraw.Draw(edges_map)
	edges = []
	for i in range(len(peaks_with_score)):
		x1, y1, s1 = peaks_with_score[i]
		peaks_map[y1, x1] = 1
		for j in range(i + 1, len(peaks_with_score)):
			x2, y2, _ = peaks_with_score[j]
			temp = Image.new('P', (w, h), color = 0)
			tmp_draw = ImageDraw.Draw(temp)
			tmp_draw.line([x1, y1, x2, y2], fill = 255, width = 1)
			temp = np.array(temp, np.float32) / 255.0
			score = np.mean(hmb[temp > 0.5])
			if score >= 0.5:
				draw.line([x1, y1, x2, y2], fill = 255, width = 1)
				edges.append((i, j, score))
	edges_map = np.array(edges_map, np.float32) / 255.0
	return edges_map, peaks_map, peaks_with_score, edges










def recoverMultiPath(img_size, paths):
	pathImgs = []
	smallImgs = []
	res = np.zeros(img_size)
	for i in range(len(paths)):
		path = []
		path_small = []
		for j in range(paths[i].shape[0]):
			hmap = paths[i][j]
			end = 1 - hmap.sum()
			ind = np.unravel_index(np.argmax(hmap), hmap.shape)
			if hmap[ind] >= end:
				path.append((ind[1] * 8 + 4, ind[0] * 8 + 4))
				path_small.append((ind[1], ind[0]))
			else:
				break
		pathImg = Image.new('P', img_size, color = 0)
		draw = ImageDraw.Draw(pathImg)
		draw.line(path, fill = 1, width = 5)
		res += np.array(pathImg, np.float32)
		###
		smallImg = Image.new('P', (round(img_size[0]/8), round(img_size[1]/8)), color = 0)
		draw = ImageDraw.Draw(smallImg)
		draw.line(path_small, fill = 1, width = 1)
		###
		pathImgs.append(np.array(pathImg, np.float32))
		smallImgs.append(np.array(smallImg, np.float32))
	res = np.array((res - res.min()) * 255.0 / (res.max() - res.min() + 1e-9), np.uint8)
	return res, pathImgs, smallImgs



def recoverEdges(pred_v_out, v_val2idx):
	def l2dist(v1, v2):
		diff = np.array(v1) - np.array(v2)
		return np.sqrt(np.dot(diff, diff))

	len_path = pred_v_out.shape[0]
	path = []
	for i in range(len_path):
		hmap = pred_v_out[i]
		end = 1 - hmap.sum()
		ind = np.unravel_index(np.argmax(hmap), hmap.shape)
		if hmap[ind] >= end:
			v = (ind[1], ind[0])
			if v in v_val2idx:
				path.append(v_val2idx[v])
			else:
				li = [(l2dist(v, v_val), i) for v_val, i in v_val2idx.items()]
				path.append(min(li)[1])
		else:
			break
	edges = []
	if len(path) > 1:
		for s, t in zip(path[:-1], path[1:]):
			if s != t:
				edges.append((s, t))
				edges.append((t, s))
	return edges



if __name__ == '__main__':
	dg = DataGenerator(sys.argv[1], config.AREA_SIZE, config.V_OUT_RES, config.MAX_NUM_VERTICES)
	for i in range(10):
		print(i)
		img, boundary, vertices, vertex_inputs, vertex_outputs, ends, seq_lens, seq_idx = dg.getAreasBatch(4, 'train')
		print(img.shape)
		print(boundary.shape)
		print(vertices.shape)
		print(vertex_inputs.shape)
		print(vertex_outputs.shape)
		print(ends.shape)
		print(seq_lens.shape)
		print(seq_idx.shape)




