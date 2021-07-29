# Irregular-occupation-detection-on-satellite-imagery

The objective of this project is to adapt, train and test a Mask R-CNN model to identify occupations in satellite imagery for regulatory purposes. The state-of-the-art architecture in question was chosen because each occupation, even if reasonably clustered, must be independently identified and accurately delimitated.

The project dataset of training and test examples contains many Km² of manually labelled occupations, regular and irregular, although it must be mentioned: initially there won't be a need to distinguish regular from irregurlar, only if there is an occupation, where and it's shape.

The implementation was made through a fork of leekunhee/Mask_RCNN repo, which is a adaptation from matterpot/Mask_RCNN to use tensorflow 2.0, alongside a few changes explained down below. For testing purposes an implementation in Pytorch was also made.
