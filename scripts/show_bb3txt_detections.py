"""
Displays given detections over images. Paths to images it takes from the detections BB3TXT file and
uses them to load images to display. If a ground truth BB3TXT file is provided it must contain
the same paths to images as the file with detections.

This program has a simple user interface where 'left' and 'right' arrow keys function as previous
and next keys. The 'q' key exits the program.

----------------------------------------------------------------------------------------------------
python show_bb3txt_detections.py path_detections detections_mapping
----------------------------------------------------------------------------------------------------
"""

__date__   = '03/18/2017'
__author__ = 'Libor Novak'
__email__  = 'novakli2@fel.cvut.cz'


import argparse
import os
from matplotlib import pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches

from data.shared.bb3txt import load_bb3txt
from data.shared.pgp import load_pgp
from data.mappings.utils import LabelMappingManager


####################################################################################################
#                                           DEFINITIONS                                            # 
####################################################################################################

# Categories (labels), which show
CATEGORIES = [
	'car',
	'person'
]

# Colors of the bounding boxes of the categories
# COLORS = [plt.cm.gist_ncar(i) for i in np.linspace(0, 1, len(CATEGORIES))]
COLORS = ['#3399FF', '#FF33CC']

# Initialize the LabelMappingManager
LMM = LabelMappingManager()


####################################################################################################
#                                            FUNCTIONS                                             # 
####################################################################################################



####################################################################################################
#                                             CLASSES                                              # 
####################################################################################################

class DetectionBrowser(object):
	"""
	"""
	def __init__(self, path_detections, detections_mapping, confidence,
				 path_gt=None, gt_mapping=None, path_datasets=None, path_pgp=None):
		"""
		Input:
			path_detections:    Path to the BB3TXT file with detections
			detections_mapping: Name of the mapping of the path_detections BB3TXT file
			confidence:         Minimum confidence of a detection to be displayed
			path_gt:            Path to the BB3TXT file with ground truth (optional)
			gt_mapping:         Name of the mapping of the path_gt BB3TXT file (optional)
			path_datasets:      Path to the "datasets" folder on this machine, replaces the path
								that is in the BB3TXT files if provided
			path_pgp:           Path to the PGP file with image projection matrices and ground plane
			                    equations
		"""
		super(DetectionBrowser, self).__init__()
		
		self.confidence = confidence
		self.path_datasets = path_datasets

		print('-- Loading detections: ' + path_detections)
		self.iml_detections     = load_bb3txt(path_detections)
		self.detections_mapping = LMM.get_mapping(detections_mapping)

		self._create_file_list()
		
		if path_gt is not None and gt_mapping is not None:
			print('-- Loading ground truth: ' + path_gt)
			self.iml_gt     = load_bb3txt(path_gt)
			self.gt_mapping = LMM.get_mapping(gt_mapping)
		else:
			self.iml_gt     = None
			self.gt_mapping = None


		if path_pgp is not None:
			print('-- Loading PGP: ' + path_pgp)
			self.pgps = load_pgp(path_pgp)
		else:
			self.pgps = None

		# Initialize the cursor to the first image
		self.cursor = 0


	def _create_file_list(self):
		"""
		Creates a sorted list of files, which we will be cycling through.
		"""
		self.file_list = self.iml_detections.keys()
		self.file_list.sort()


	def _on_key_press_event(self, event):
		"""
		This method is called when a key is pressed while browsing. Moves the cursor and reloads
		the canvas with the image.

		Input:
			event: key_press_event
		"""
		if event.key == 'left':
			# Previous
			self.cursor = (len(self.file_list) + self.cursor - 1) % len(self.file_list)
			self._render()
		elif event.key == 'right':
			# Next
			self.cursor = (self.cursor + 1) % len(self.file_list)
			self._render()
		if event.key == 'w':
			# Previous 200
			self.cursor = (len(self.file_list) + self.cursor - 200) % len(self.file_list)
			self._render()
		elif event.key == 'e':
			# Next 200
			self.cursor = (self.cursor + 200) % len(self.file_list)
			self._render()
		elif event.key == 'up':
			# Increase confidence threshold
			self.confidence += 0.05
			self._render()
		elif event.key == 'down':
			# Decrease confidence threshold
			self.confidence -= 0.05
			self._render()
		elif event.key == 'q':
			# Quit
			plt.close()
		else:
			return


	def _render(self):
		"""
		Render the current cursor image into the canvas.
		"""
		# If path to datasets folder is provided we need to exchange the path in the path to
		# the image in order to be able to load the image
		if self.path_datasets is not None:
			path_image = self.file_list[self.cursor]
			# Find the position of the "datasets" folder in the path
			pos = path_image.find('/datasets/') + 1
			if pos >= 0:
				path_image = os.path.join(self.path_datasets, path_image[pos:])
			img = mpimg.imread(path_image)
		else:
			img = mpimg.imread(self.file_list[self.cursor])

		# Render
		self.ax1.cla()
		if self.ax2 is not None: self.ax2.cla()
		self.ax1.imshow(img)

		self.ax1.set_xlim([0, img.shape[1]])
		self.ax1.set_ylim([img.shape[0], 0])
		if self.ax2 is not None: self.ax2.set_xlim([-40, 40])
		if self.ax2 is not None: self.ax2.set_ylim([-5, 140])

		if self.iml_gt is not None:
			self._render_3d_boxes(self.iml_gt, self.gt_mapping, gt=True)
		self._render_3d_boxes(self.iml_detections, self.detections_mapping)

		self.fig.suptitle('[' + str(self.cursor) + '/' + str(len(self.file_list)) + '] ' + self.file_list[self.cursor] + ' (((' + str(self.confidence) + ')))')
		self.ax1.set_axis_off()
		if self.ax2 is not None: self.ax2.set_aspect('equal')
		self.fig.canvas.draw()
		plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)


	def _render_3d_boxes(self, iml, mapping, gt=False):
		"""
		Renders 3D bounding boxes from the given list on the current image.

		Input:
			iml:     Image list (either self.iml_gt or self.iml_detections)
			mapping: Label mapping of the dataset (either self.gt_mapping or self.detections_mapping)
			gt:      True if the rendered bounding boxes are ground truth
		"""
		filename = self.file_list[self.cursor]

		if filename in iml:
			# Plot the position of the camera into the world coordinates
			if self.pgps is not None and filename in self.pgps:
				pgp = self.pgps[filename]
				# Camera misplacement line
				self.ax2.plot([pgp.C_3x1[0,0], pgp.C_3x1[0,0]], [-10, 150], color='#CCCCCC', linewidth=4)

			for bb in iml[filename]:
				if mapping[bb.label] in CATEGORIES and (gt or bb.confidence >= self.confidence):
					# Index of the category in CATEGORIES
					id = CATEGORIES.index(mapping[bb.label])
					color = '#ffd633' if gt else COLORS[id]  # Ground truth has always the same color

					# rect = patches.Rectangle((bb.bb2d.xmin, bb.bb2d.ymin), bb.bb2d.width(), 
					# 						  bb.bb2d.height(), linewidth=1, edgecolor=color,
					# 						  facecolor='none')
					# self.ax1.add_patch(rect)

					if self.pgps is not None:
						# We have image projection matrices and ground plane - reconstruct the whole
						# 3d box
						if filename in self.pgps:
							pgp = self.pgps[filename]

							# Get all 4 bounding box corners in 3D (FBL FBR RBR RBL FTL FTR RTR RTL)
							X_3x8 = pgp.reconstruct_bb3d(bb)

							# Draw bb on the xz plane
							self.ax2.plot([X_3x8[0,0], X_3x8[0,1]], [X_3x8[2,0], X_3x8[2,1]], color='#00FF00', linewidth=2)
							self.ax2.plot([X_3x8[0,0], X_3x8[0,3]], [X_3x8[2,0], X_3x8[2,3]], color=color, linewidth=2)
							self.ax2.plot([X_3x8[0,1], X_3x8[0,2]], [X_3x8[2,1], X_3x8[2,2]], color=color, linewidth=2)
							self.ax2.plot([X_3x8[0,2], X_3x8[0,3]], [X_3x8[2,2], X_3x8[2,3]], color='#FF0000', linewidth=2)

							# Project them back to image
							x_2x8 = pgp.project_X_to_x(X_3x8)

							# Plot front side
							self.ax1.plot([x_2x8[0,4], x_2x8[0,5]], [x_2x8[1,4], x_2x8[1,5]], color='g', linewidth=2)
							self.ax1.plot([x_2x8[0,5], x_2x8[0,1]], [x_2x8[1,5], x_2x8[1,1]], color='g', linewidth=2)
							self.ax1.plot([x_2x8[0,0], x_2x8[0,1]], [x_2x8[1,0], x_2x8[1,1]], color='g', linewidth=2)
							self.ax1.plot([x_2x8[0,0], x_2x8[0,4]], [x_2x8[1,0], x_2x8[1,4]], color='g', linewidth=2)
							# Plot rear side
							self.ax1.plot([x_2x8[0,2], x_2x8[0,3]], [x_2x8[1,2], x_2x8[1,3]], color='r', linewidth=2)
							self.ax1.plot([x_2x8[0,7], x_2x8[0,3]], [x_2x8[1,7], x_2x8[1,3]], color='r', linewidth=2)
							self.ax1.plot([x_2x8[0,7], x_2x8[0,6]], [x_2x8[1,7], x_2x8[1,6]], color='r', linewidth=2)
							self.ax1.plot([x_2x8[0,6], x_2x8[0,2]], [x_2x8[1,6], x_2x8[1,2]], color='r', linewidth=2)
							# Plot connections
							self.ax1.plot([x_2x8[0,4], x_2x8[0,7]], [x_2x8[1,4], x_2x8[1,7]], color=color, linewidth=2)
							self.ax1.plot([x_2x8[0,5], x_2x8[0,6]], [x_2x8[1,5], x_2x8[1,6]], color=color, linewidth=2)
							self.ax1.plot([x_2x8[0,1], x_2x8[0,2]], [x_2x8[1,1], x_2x8[1,2]], color=color, linewidth=2)
							self.ax1.plot([x_2x8[0,0], x_2x8[0,3]], [x_2x8[1,0], x_2x8[1,3]], color=color, linewidth=2)

						else:
							print('WARNING: PGP entry not found for image: "' + filename + '"')
						
					else:
						# Plot the available corners
						self.ax1.plot([bb.fblx, bb.fbrx], [bb.fbly, bb.fbry], color='g', linewidth=2)
						self.ax1.plot([bb.fblx, bb.fblx], [bb.fbly, bb.ftly], color='g', linewidth=2)
						self.ax1.plot([bb.fblx, bb.rblx], [bb.fbly, bb.rbly], color=color, linewidth=2)

					txt = mapping[bb.label] if gt else mapping[bb.label] + ' %.3f'%(bb.confidence)
					self.ax1.text(bb.fblx, bb.ftly-5, txt, fontsize=15, color=color)


	def browse(self, offset=0):
		"""
		Displays the browser and allows the user to flick through the images in the file_list.

		Input:
			offset:        Number of an image that we want to start with
		"""
		self.cursor = offset

		# Create the interactive window
		self.fig = plt.figure()
		if self.pgps is not None:
			self.ax1 = plt.subplot2grid((1,3), (0,0), colspan=2)
			self.ax2 = plt.subplot2grid((1,3), (0,2))
		else:
			self.ax1 = plt.subplot2grid((1,1), (0,0))
			self.ax2 = None
		self.fig.canvas.mpl_connect('key_press_event', self._on_key_press_event)

		self._render()

		# Display controls
		print('-- CONTROLS:')
		print('--     "left key"   previous image')
		print('--     "right key"  next image')
		print('--     "w"          jump 200 images backward')
		print('--     "e"          jump 200 images forward')
		print('--     "up key"     raise confidence threshold by 0.05')
		print('--     "down key"   decrease confidence threshold by 0.05')
		print('--     "q"          quit the program')

		plt.show()



####################################################################################################
#                                               MAIN                                               # 
####################################################################################################

def check_path(path, is_folder=False):
	"""
	Checks if the given path exists.

	Input:
		path:      Path to be checked
		is_folder: True if the checked path is a folder
	Returns:
		True if the given path exists
	"""
	if not os.path.exists(path) or (not is_folder and not os.path.isfile(path)):
		print('ERROR: Path "%s" does not exist!'%(path))
		return False

	return True


def parse_arguments():
	"""
	Parse input options of the script.
	"""
	parser = argparse.ArgumentParser(description='Plot the precision/recall curve.')
	parser.add_argument('path_detections', metavar='path_detections', type=str,
						help='Path to the BB3TXT file with detections to be shown')
	parser.add_argument('detections_mapping', metavar='detections_mapping', type=str,
						help='Label mapping of the detections BB3TXT file. One of ' \
						+ str(LMM.available_mappings()))
	parser.add_argument('--path_gt', type=str, default=None,
						help='Path to the BB3TXT ground truth file (also --gt_mapping is required)')
	parser.add_argument('--gt_mapping', type=str, default=None,
						help='Label mapping of the ground truth BB3TXT file. One of ' \
						+ str(LMM.available_mappings()))
	parser.add_argument('--confidence', type=float, default=0.5,
						help='Minimum confidence of shown bounding boxes')
	parser.add_argument('--path_datasets', type=str, default=None,
						help='Path to the "datasets" folder on this machine - will be used to ' \
						'replace the path from the test and gt BB3TXT files so we could show the ' \
						'images even if the test was carried out on a different PC')
	parser.add_argument('--path_pgp', type=str, default=None,
						help='Path to the PGP file with image projection matrices and ground ' \
						'plane equations. This allows showing the whole 3D bounding box with ' \
						'projection to the xz plane')

	args = parser.parse_args()

	if not check_path(args.path_detections) or \
			(args.path_gt is not None and not check_path(args.path_gt)) or \
			(args.path_datasets is not None and not check_path(args.path_datasets, True)) or \
			(args.path_pgp is not None and not check_path(args.path_pgp)):
		parser.print_help()
		exit(1)

	if args.path_gt is not None and args.gt_mapping is None:
		print('ERROR: Label mapping for ground truth must be provided if ground truth is provided!')
		exit(1)

	return args


def main():
	args = parse_arguments()

	print('-- DETECTION BROWSER')

	browser = DetectionBrowser(args.path_detections, args.detections_mapping, args.confidence,
							   args.path_gt, args.gt_mapping, args.path_datasets, args.path_pgp)
	browser.browse()


if __name__ == '__main__':
    main()


