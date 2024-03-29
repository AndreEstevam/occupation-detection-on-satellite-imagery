"""
Subclasses from torch's Dataset class, used to feed the DataLoader. EdfDataset for samples extracted via ArcGIS
and CrowdDataset for AIcrowd's samples.
"""
import os
import numpy as np
import torch
from PIL import Image

from my_utils import load_image_as_np_array, extract_masks_from_cluster, extract_bboxes_from_mask

from pycocotools import COCO


class EdfDataset(torch.utils.data.Dataset):
    def __init__(self, dataset_dir, transforms):
        img_dir = os.path.join(dataset_dir, 'image')
        label_dir = os.path.join(dataset_dir, 'label')
        self.img_paths = [os.path.join(img_dir, img) for img in sorted(os.listdir(img_dir))]
        self.mask_paths = [os.path.join(label_dir, mask) for mask in sorted(os.listdir(label_dir))]
        self.transforms = transforms


    def __getitem__(self, idx):
        '''
        Args:
            idx: index of sample to be fed
        return:
            - PIL Image of shape (H, W)
            - target (dict) containing: 
                - boxes:    FloatTensor[N, 4], N being the n° of instances and it's bounding 
                boxe coordinates in [x0, y0, x1, y1] format, ranging from 0 to W and 0 to H;
                - labels:   Int64Tensor[N], class label (0 is background);
                - image_id: Int64Tensor[1], unique id for each image;
                - area:     Tensor[N], area of bbox;
                - iscrowd:  UInt8Tensor[N], True or False;
                - masks:    UInt8Tensor[N, H, W], segmantation maps;
        '''
        img = Image.open(self.img_paths[idx]).convert("RGB")

        mask = load_image_as_np_array(self.mask_paths[idx])
        mask_ch_first = extract_masks_from_cluster(mask, bool_array=True, ch_first=True)
        bboxes = extract_bboxes_from_mask(np.dstack(mask_ch_first))
        num_instaces = np.shape(mask_ch_first)[0]
        
        boxes = torch.as_tensor(bboxes, dtype=torch.float32)
        labels = torch.ones((num_instaces,), dtype=torch.int64)
        masks = torch.as_tensor(mask_ch_first, dtype=torch.uint8)
        image_id = torch.tensor([idx])
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])
        iscrowd = torch.zeros((num_instaces,), dtype=torch.int64)

        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        target["masks"] = masks
        target["image_id"] = image_id
        target["area"] = area
        target["iscrowd"] = iscrowd

        if self.transforms is not None:
            img, target = self.transforms(img, target)
        return img, target



    def __len__(self):
        return len(self.img_paths)


    def check(self):
        for i, j in zip(self.img_paths, self.mask_paths):
            if i[-9:-4] != j[-9:-4]:
                print("Image and label do not match.")
                break

class CrowdDataset(torch.utils.data.Dataset):
    def __init__(self, dataset_dir, subset, transforms, load_small=False):
        dataset_path = os.path.join(dataset_dir, subset)
        if load_small:
            ann_file = os.path.join(dataset_path, "annotation-small.json")
        else:
            ann_file = os.path.join(dataset_path, "annotation.json")
        self.imgs_dir = os.path.join(dataset_path, "images")
        self.coco = COCO(ann_file)
        self.img_ids = sorted(self.coco.getImgIds())
        self.transforms = transforms


    def __getitem__(self, idx):
        '''
        Args:
            idx: index of sample to be fed
        return:
            - PIL Image of shape (H, W)
            - target (dict) containing: 
                - boxes:    FloatTensor[N, 4], N being the n° of instances and it's bounding 
                boxe coordinates in [x0, y0, x1, y1] format, ranging from 0 to W and 0 to H;
                - labels:   Int64Tensor[N], class label (0 is background);
                - image_id: Int64Tensor[1], unique id for each image;
                - area:     Tensor[N], area of bbox;
                - iscrowd:  UInt8Tensor[N], True or False;
                - masks:    UInt8Tensor[N, H, W], segmantation maps;
        '''
        # Selecting sample
        image_id = self.img_ids[idx]

        # Getting image
        img_obj = self.coco.loadImgs(image_id)[0]
        image = Image.open(os.path.join(self.imgs_dir, img_obj['file_name']))

        # Getting annotations
        anno = self.coco.loadAnns(self.coco.getAnnIds(image_id)) 
        anno = [obj for obj in anno if obj['iscrowd'] == 0]         # necessary?

        # Getting labels
        classes = torch.ones(len(anno), dtype=torch.int64)

        # Getting masks
        masks_np = np.array([self.coco.annToMask(obj) for obj in anno])
        masks = torch.as_tensor(masks_np, dtype=torch.uint8)
        
        # Extracting bboxes from masks
        boxes = extract_bboxes_from_mask(np.dstack(masks_np))
        boxes = torch.as_tensor(boxes, dtype=torch.float32)

        # Selecting valid instances
        keep = (boxes[:, 3] > boxes[:, 1]) & (boxes[:, 2] > boxes[:, 0])
        boxes = boxes[keep]
        classes = classes[keep]
        masks = masks[keep]

        image_id = torch.tensor([image_id])
        area = torch.tensor([obj["area"] for obj in anno])
        iscrowd = torch.tensor([obj["iscrowd"] for obj in anno])

        target = {}
        target["boxes"] = boxes
        target["labels"] = classes
        target["masks"] = masks
        target["image_id"] = image_id
        target["area"] = area
        target["iscrowd"] = iscrowd

        if self.transforms is not None:
            image, target = self.transforms(image, target)

        return image, target


    def __len__(self):
        return len(self.img_ids)
