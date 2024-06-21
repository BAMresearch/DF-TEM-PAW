import struct
from omero.model.enums import UnitsLength
from omero.model import RoiI, MaskI, ImageI, PolygonI, LengthI
from omero.gateway import BlitzGateway, rint, rdouble, rstring
import numpy as np
import math
import cv2
import omero.clients

class OmeroConnect:
    def __init__(self, host, username, password):
        self.client = omero.client(host)
        self.username=username
        self.password=password
        self.test_connect()

    def test_connect(self):
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            print("Connected as {}".format(conn.getUser().getName()))
            print("User ID: {}".format(conn.getUser().getId()))
            print("User Full Name: {}".format(conn.getUser().getFullName()))

            print("Your Groups:")
            for g in conn.getGroupsMemberOf():
                print("   Name:", g.getName(), " ID:", g.getId())
            group = conn.getGroupFromContext()
            print("Current group: ", group.getName())

    def get_projects(self):
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            projects = conn.listProjects()
            return [{"name": p.getName(), "details": p.getDetails()} for p in projects]

    def get_datasets(self, project_id: int):
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            # demo project
            project = conn.getObject("Project", project_id)
            return list(project.listChildren())

    # Load images in a specified dataset method


    def get_images(self, dataset_id: int):
        """
        Load the images in the specified dataset
        :param conn: The BlitzGateway
        :param dataset_id: The dataset's id
        :return: The Images or None
        """
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            dataset = conn.getObject("Dataset", dataset_id)
            images = []
            if dataset:
                for image in dataset.listChildren():
                    images.append(image)
                if len(images) == 0:
                    return None

            for image in images:
                print("---- Loaded image ID:", image.id)

            # Print dataset ID and name
            print("Dataset ID:", dataset.getId())
            print("Dataset Name:", dataset.getName())
        return images


    def create_roi(self, img_id: int, shapes):
        # create an ROI, link it to Image
        roi = RoiI()
        # use the omero.model.ImageI that underlies the 'image' wrapper
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            img = conn.getObject("Image", img_id)
            roi.setImage(ImageI(img_id, False))
            for shape in shapes:
                roi.addShape(shape)
            # Save the ROI (saves any linked shapes too)
            updateService = conn.getUpdateService()
            return updateService.saveAndReturnObject(roi)


    def delete_rois(self, image_id: int):
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            roi_service = conn.getRoiService()
            result = roi_service.findByImage(image_id, None)
            roi_ids = [roi.id.val for roi in result.rois]
            if roi_ids:
                conn.deleteObjects("Roi", roi_ids)
            print("deleted rois: {}".format(roi_ids))



    def print_image_details(self, img_id: int):
        # Retrieve information about the image
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            image = conn.getObject("Image", img_id)
            print("Image Name:", image.getName())
            print("Image Name:", image.id)
            print("Image Description:", image.getDescription())
            print("Image SizeX:", image.getSizeX())
            print("Image SizeY:", image.getSizeY())
            print("Image SizeZ:", image.getSizeZ())
            print("Image SizeC:", image.getSizeC())
            print("Image SizeT:", image.getSizeT())

            x = image.getName()

            # List Channels (loads the Rendering settings to get channel colors)
            for channel in image.getChannels():
                print('Channel:', channel.getLabel())
                print('Color:', channel.getColor().getRGB())
                print('Lookup table:', channel.getLut())
                print('Is reverse intensity?', channel.isReverseIntensity())

            print(image.countImportedImageFiles())
            file_count = image.countFilesetFiles()
            # list files
            if file_count > 0:
                for orig_file in image.getImportedImageFiles():
                    name = orig_file.getName()
                    path = orig_file.getPath()
                    print(name)
                    print(path)
        return x


    def get_grayscale(self, img_id: int):
        session = self.client.createSession(self.username, self.password)
        with BlitzGateway(client_obj=self.client) as conn:
            image = conn.getObject("Image", img_id)
            z = image.getSizeZ() / 2
            t = 0
            rendered_image = image.renderImage(z, t)
            image_array = np.asarray(rendered_image)
            # Convert the image to grayscale
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        return gray


    def create_omero_roi_polygons(self, image_id: int, contours):
        the_t = 0
        the_z = 0
        polygons = []
        # create an ROI with a single polygon
        for i, contour in enumerate(contours):
            polygon = PolygonI()
            polygon.theZ = rint(the_z)
            polygon.theT = rint(the_t)
            color = list(np.random.choice(range(256), size=3))
            polygon.strokeColor = rint(rgba_to_int(color[0], color[1], color[2]))
            polygon.fillColor = rint(rgba_to_int(color[0], color[1], color[2]))

            polygon.strokeWidth = LengthI(1, UnitsLength.PIXEL)
            pts = ["{},{}".format(point[:, 0][0], point[:, 1][0])
                for point in contour]
            pts_list = " ".join(pts)
            polygon.points = rstring(pts_list)
            # print(pts_list[:30])
            polygon.textValue = rstring("Precipitate"+str(i))
            polygons.append(polygon)
        # print(polygon.info())
        # print(polygon.__dir__())
        self.create_roi(image_id, polygons)
        print("added {} polygon shapes to image".format(len(polygons)))

def create_mask(mask_bytes, bytes_per_pixel=1):
    if bytes_per_pixel == 2:
        divider = 16.0
        format_string = "H"  # Unsigned short
        byte_factor = 0.5
    elif bytes_per_pixel == 1:
        divider = 8.0
        format_string = "B"  # Unsigned char
        byte_factor = 1
    else:
        message = "Format %s not supported"
        raise ValueError(message)
    steps = math.ceil(len(mask_bytes) / divider)
    mask = []
    for i in range(int(steps)):
        binary = mask_bytes[
            i * int(divider):i * int(divider) + int(divider)]
        format = str(int(byte_factor * len(binary))) + format_string
        binary = struct.unpack(format, binary)
        s = ""
        for bit in binary:
            s += str(bit)
        mask.append(int(s, 2))
    return bytearray(mask)

def rgba_to_int(red, green, blue, alpha=255):
    """ Return the color as an Integer in RGBA encoding """
    return int.from_bytes([red, green, blue, alpha],
                          byteorder='big', signed=True)
