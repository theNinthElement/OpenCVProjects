import numpy as np
import os
import time
import cv2 as cv
from numpy.linalg import lstsq
import matplotlib.pyplot as plt



def load_FLO_file(filename):
    assert os.path.isfile(filename), 'file does not exist: ' + filename   
    flo_file = open(filename,'rb')
    magic = np.fromfile(flo_file, np.float32, count=1)
    assert magic == 202021.25,  'Magic number incorrect. .flo file is invalid';
    w = np.fromfile(flo_file, np.int32, count=1)
    h = np.fromfile(flo_file, np.int32, count=1)
    data = np.fromfile(flo_file, np.float32, count=2*w[0]*h[0])
    flow = np.resize(data, (int(h[0]), int(w[0]), 2))
    flo_file.close()
    return flow

class OpticalFlow:
    def __init__(self):
        # Parameters for Lucas_Kanade_flow()
        self.EIGEN_THRESHOLD = 0.01 # use as threshold for determining if the optical flow is valid when performing Lucas-Kanade
        self.WINDOW_SIZE = [25, 25] # the number of points taken in the neighborhood of each pixel

        # Parameters for Horn_Schunck_flow()
        self.EPSILON= 0.002 # the stopping criterion for the difference when performing the Horn-Schuck algorithm
        self.MAX_ITERS = 200 # maximum number of iterations allowed until convergence of the Horn-Schuck algorithm
        self.ALPHA = 1.0 # smoothness term

        # Parameter for flow_map_to_bgr()
        self.UNKNOWN_FLOW_THRESH = 1000

        self.prev = None
        self.next = None

    def next_frame(self, img):
        self.prev = self.next
        self.next = img

        if self.prev is None:
            return False

        frames = np.float32(np.array([self.prev, self.next]))
        frames /= 255.0

        #calculate image gradient
        self.Ix = cv.Sobel(frames[0], cv.CV_32F, 1, 0, 3)
        self.Iy = cv.Sobel(frames[0], cv.CV_32F, 0, 1, 3)
        self.It = frames[1]-frames[0]

        return True

    #***********************************************************************************
    # function for converting flow map to to BGR image for visualisation
    # return bgr image
    def flow_map_to_bgr(self, flow, step=7):
        flow_bgr = None
       
        return flow_bgr

    #***********************************************************************************
    # implement Lucas-Kanade Optical Flow 
    # returns the Optical flow based on the Lucas-Kanade algorithm and visualisation result
    def Lucas_Kanade_flow(self):
        flow = None
        filterWindow = np.ones((25,25))
        
        U = np.zeros([self.prev.shape[0],self.prev.shape[1]])
        V = np.zeros([self.prev.shape[0],self.prev.shape[1]])
        
        #flow = ((U,V))
        flow = np.zeros((self.prev.shape[0], self.prev.shape[1], 2))
        
        self.sigma_Ixx = cv.filter2D (self.Ix**2,-1,filterWindow)
        self.sigma_Iyy = cv.filter2D (self.Iy**2,-1,filterWindow)
        self.sigma_Ixy = cv.filter2D (self.Ix*self.Iy,-1,filterWindow)
        self.sigma_Ixt = cv.filter2D (self.Ix*self.It,-1,filterWindow)
        self.sigma_Iyt = cv.filter2D (self.Iy*self.It,-1,filterWindow)
        
        
        for i in range(self.Ix.shape[0]):
            for j in range (self.Ix.shape[1]) :
                AtA = np.array([[self.sigma_Ixx[i,j],self.sigma_Ixy[i,j]],
                                [self.sigma_Ixy[i,j],self.sigma_Iyy[i,j]]])
                AtA = AtA.astype(float)
                At = -np.array([self.sigma_Ixt[i,j], self.sigma_Iyt[i,j]])
                At = At.astype(float)
               # print("Ata : " ,AtA)
                #print("At : " , At)
                leastSq,resids, rank, s = lstsq (AtA, At, rcond='warn')
                #print("ls : " , leastSq[0])
                #print (leastSq)
               # U[i,j] = leastSq[0]
               # V[i,j] = leastSq[1]
                flow[i][j] = leastSq
        
        flow_bgr = self.flow_map_to_bgr(flow)
        return flow, flow_bgr

    #***********************************************************************************
    # implement Horn-Schunck Optical Flow 
    # returns the Optical flow based on the Horn-Schunck algorithm and visualisation result
    def Horn_Schunck_flow(self):
        flow = None
        LapKernel = np.array([[0, 1/4, 0],
                  [1/4,    -1, 1/4],
                  [0, 1/4, 0]],float)        

        U = np.zeros([self.prev.shape[0],self.prev.shape[1]])
        V = np.zeros([self.prev.shape[0],self.prev.shape[1]])       

	    # iterate to refine U,V
        for i in range(self.MAX_ITERS):
            # Laplacian ==> f-fav 
            Un_av = cv.filter2D(U,-1, LapKernel) + U
            Vn_av = cv.filter2D(V,-1, LapKernel) + V

            derivatives = (self.Ix*Un_av + self.Iy*Vn_av + self.It) / (self.ALPHA**2 + self.Ix**2 + self.Iy**2)

            U = Un_av - self.Ix * derivatives
            V = Vn_av - self.Iy * derivatives
            
            if checkL2(U, Un_av, V, Vn_av):
                break
        
        flow = (U,V,2)
        
        flow_bgr = self.flow_map_to_bgr((U, V))
        return (U, V), flow_bgr

    #***********************************************************************************
    #calculate the angular error here
    # return average angular error and per point error map
    def calculate_angular_error(self, estimated_flow, groundtruth_flow):
        aae = None
        aae_per_point = None
        
        print("Here it is : " ,estimated_flow.shape)
        u_v_t = estimated_flow.reshape((estimated_flow.shape[0] * estimated_flow.shape[1],estimated_flow.shape[2]))
        uc_vc_t = groundtruth_flow.reshape((groundtruth_flow.shape[0] * groundtruth_flow.shape[1],estimated_flow.shape[2]))
        
        step1 = np.arccos((uc_vc_t[:,0]*u_v_t[:,0]+uc_vc_t[:,1]*u_v_t[:,1]+1)/\
                          np.sqrt((np.square(uc_vc_t[:,0])+np.square(uc_vc_t[:,1])+1)*\
                                  (np.square(u_v_t[:,0])+np.square(u_v_t[:,1])+1)))
        #print(step1)
        n = step1.shape[0]
        #print(n)
        aae = (1/n) * np.sum(step1)        
        #print(aae)
        aae_per_point = step1
        
        return aae, aae_per_point

def showImg(img, name="Image.png"):
    cv.imwrite(name,img) 
    #cv.waitKey(0) 
    #cv.destroyAllWindows()

def checkL2(U, Uav, V, Vav):
    row = U.shape[0]
    col = U.shape[1]

    error = 0
    for i in range(row):
        for j in range(col):
            error += (abs(U[i][j]-Uav[i][j]) + abs(V[i][j]-Vav[i][j]))
            if error > 0.002:
                return False
    return True
    

if __name__ == "__main__":

    data_list = [
        'data/frame_0001.png',
        'data/frame_0002.png',
        'data/frame_0007.png',
    ]

    gt_list = [
        './data/frame_0001.flo',
        './data/frame_0002.flo',
        './data/frame_0007.flo',
    ]

    Op = OpticalFlow()
    j =0 
    for (i, (frame_filename, gt_filemane)) in enumerate(zip(data_list, gt_list)):
        groundtruth_flow = load_FLO_file(gt_filemane)
        img = cv.cvtColor(cv.imread(frame_filename), cv.COLOR_BGR2GRAY)
        
        if not Op.next_frame(img):
            continue

        flow_lucas_kanade, flow_lucas_kanade_bgr = Op.Lucas_Kanade_flow()
        aae_lucas_kanade, aae_lucas_kanade_per_point = Op.calculate_angular_error(flow_lucas_kanade, groundtruth_flow)
        #print('Average Angular error for Luacas-Kanade Optical Flow: %.4f' %(aae_lucas_kanade))

        flow_horn_schunck, flow_horn_schunck_bgr = Op.Horn_Schunck_flow()
        #print(flow_horn_schunck)
        #aae_horn_schunk, aae_horn_schunk_per_point = Op.calculate_angular_error(flow_horn_schunck, groundtruth_flow)        
        #print('Average Angular error for Horn-Schunck Optical Flow: %.4f' %(aae_horn_schunk))   

        #flow_bgr_gt = Op.flow_map_to_bgr(groundtruth_flow)

        #fig = plt.figure(figsize=(img.shape))
    
        # Display
        #fig.add_subplot(2, 3, 1)
        #plt.imshow(flow_bgr_gt)
        #fig.add_subplot(2, 3, 2)
        #plt.imshow(flow_lucas_kanade_bgr)
        #fig.add_subplot(2, 3, 3)
        #plt.imshow(aae_lucas_kanade_per_point)
        #fig.add_subplot(2, 3, 4)
        #plt.imshow(flow_bgr_gt)
        #fig.add_subplot(2, 3, 5)
        #plt.imshow(flow_horn_schunck_bgr)
        #fig.add_subplot(2, 3, 6)
        #plt.imshow(aae_horn_schunk_per_point)
        #plt.show()
        
        # Just for testing
        #print(flow_lucas_kanade.shape)
        #print(flow_horn_schunck)
        U = flow_lucas_kanade[:,:,0]
        V = flow_lucas_kanade[:,:,1]
        A = U.copy()
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                A[i][j] = pow(U[i][j]*U[i][j] + V[i][j]*V[i][j],0.5)
        ma = np.amax(A)
        mi = np.amin(A)

        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                img[i][j] = int(255 * (A[i][j]-mi)/(ma-mi) )
        showImg(img, "Lucas_"+str(j)+".png")
        
        U = flow_horn_schunck[0]
        V = flow_horn_schunck[1]
        A = U.copy()
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                A[i][j] = pow(U[i][j]*U[i][j] + V[i][j]*V[i][j],0.5)
        ma = np.amax(A)
        mi = np.amin(A)

        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                img[i][j] = int(255 * (A[i][j]-mi)/(ma-mi) )
        showImg(img, "horn_schunck"+str(j)+".png")
        j +=1
        
        print("*"*20)
