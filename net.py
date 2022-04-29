# -*- coding: utf-8 -*-
"""net.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13oKE5ZEXudDDyWvoHd2Wc9u-asz-5QyR
"""

# delete this cell if working on Pycharm
# !pip install Bio
# !pip install import-ipynb
#
# !pip install wandb


# print(len(tf.config.list_physical_devices('GPU')))
#
# from google.colab import drive
# drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.

import tensorflow as tf
from tensorflow.keras import layers
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import KFold
import wandb
from datetime import datetime
import utils

# so we can import utils notebook (delete if working on Pycharm), you might need to change it to your working directory path
# %cd "/content/drive/MyDrive/ColabNotebooks"
# import import_ipynb


###############################################################################
#                                                                             #
#              Parameters you can change, but don't have to                   #
#                                                                             #
###############################################################################


# number of ResNet blocks for the first ResNet and the kernel size.
RESNET_1_BLOCKS = 3
RESNET_1_KERNEL_SIZE = 15
RESNET_1_KERNEL_NUM = 64

###############################################################################
#                                                                             #
#                        Parameters you need to choose                        #
#                                                                             #
###############################################################################


# number of ResNet blocks for the second ResNet, dilation list to repeat and the kernel size.

RESNET_2_BLOCKS = 1
RESNET_2_KERNEL_SIZE = 1  # good start may be 3/5
RESNET_2_KERNEL_NUM = 3
DILATION = [1]
WANTED_M = 1  # len of DILATION to be randomize by 'wandb' tool

# percentage of dropout for the dropout layer
DROPOUT = 0.0  # good start may be 0.1-0.5

# number of epochs, Learning rate and Batch size
EPOCHS = 3
LR = 0.001  # good start may be 0.0001/0.001/0.01
BATCH = 128  # good start may be 32/64/128


def get_time():
    now = datetime.now()
    return now.strftime("%d-%m-%Y__%H-%M-%S")


def resnet_block(input_layer, kernel_size, kernel_num, dialation=1):
    bn1 = layers.BatchNormalization()(input_layer)
    conv1d_layer1 = layers.Conv1D(kernel_num, kernel_size, padding='same', activation='relu',
                                  dilation_rate=dialation)(bn1)
    bn2 = layers.BatchNormalization()(conv1d_layer1)
    conv1d_layer2 = layers.Conv1D(kernel_num, kernel_size, padding='same', activation='relu',
                                  dilation_rate=dialation)(bn2)
    return layers.Add()([input_layer, conv1d_layer2])


def resnet_1(input_layer, block_num=RESNET_1_BLOCKS, kernel_size=RESNET_1_KERNEL_SIZE,
             kernel_num=RESNET_1_KERNEL_NUM):
    """
    ResNet layer - input -> BatchNormalization -> Conv1D -> Relu -> BatchNormalization -> Conv1D -> Relu -> Add
    :param input_layer: input layer for the ResNet
    :return: last layer of the ResNet
    """
    last_layer_output = input_layer

    for i in range(block_num):
        last_layer_output = resnet_block(last_layer_output, kernel_size, kernel_num)

    return last_layer_output


def resnet_2(input_layer, block_num=RESNET_2_BLOCKS, kernel_size=RESNET_2_KERNEL_SIZE,
             kernel_num=RESNET_2_KERNEL_NUM, dial_lst=DILATION):
    """
    Dilated ResNet layer - input -> BatchNormalization -> dilated Conv1D -> Relu -> BatchNormalization -> dilated Conv1D -> Relu -> Add
    :param input_layer: input layer for the ResNet
    :return: last layer of the ResNet
    """
    last_layer_output = input_layer

    for i in range(block_num):
        for d in dial_lst:
            last_layer_output = resnet_block(last_layer_output, kernel_size, kernel_num, d)

    return last_layer_output


def build_network(config):
    """
    builds the neural network architecture as shown in the exercise.
    :return: a Keras Model
    """
    dialation = [config[f"DILATION_{i}"] for i in range(WANTED_M)]
    # input, shape (NB_MAX_LENGTH,FEATURE_NUM)
    input_layer = tf.keras.Input(shape=(utils.NB_MAX_LENGTH, utils.FEATURE_NUM))

    # Conv1D -> shape = (NB_MAX_LENGTH, RESNET_1_KERNEL_NUM)
    conv1d_layer = layers.Conv1D(config['RESNET_1_KERNEL_NUM'], config['RESNET_1_KERNEL_SIZE'],
                                 padding='same')(input_layer)

    # first ResNet -> shape = (NB_MAX_LENGTH, RESNET_1_KERNEL_NUM)
    resnet_layer = resnet_1(conv1d_layer, config['RESNET_1_BLOCKS'], config['RESNET_1_KERNEL_SIZE'],
                            config['RESNET_1_KERNEL_NUM'])

    # Conv1D -> shape = (NB_MAX_LENGTH, RESNET_2_KERNEL_NUM)
    conv1d_layer = layers.Conv1D(config['RESNET_2_KERNEL_NUM'], config['RESNET_2_KERNEL_SIZE'],
                                 padding="same")(resnet_layer)

    # second ResNet -> shape = (NB_MAX_LENGTH, RESNET_2_KERNEL_NUM)
    resnet_layer = resnet_2(conv1d_layer, config['RESNET_2_BLOCKS'], config['RESNET_2_KERNEL_SIZE'],
                            config['RESNET_2_KERNEL_NUM'], dialation)

    dp = layers.Dropout(config['DROPOUT'])(resnet_layer)
    conv1d_layer = layers.Conv1D(config['RESNET_2_KERNEL_NUM'] // 2, config['RESNET_2_KERNEL_SIZE'],
                                 padding="same",
                                 activation='elu')(dp)
    dense = layers.Dense(15)(conv1d_layer)

    return tf.keras.Model(input_layer, dense)


def plot_val_train_loss(history):
    """
    plots the train and validation loss of the model at each epoch, saves it in 'model_loss_history.png'
    :param history: history object (output of fit function)
    :return: None
    """
    ig, axes = plt.subplots(1, 1, figsize=(15, 3))
    axes.plot(history.history['loss'], label='Training loss')
    axes.plot(history.history['val_loss'], label='Validation loss')
    axes.legend()
    axes.set_title("Train and Val MSE loss")

    plt.savefig("/content/drive/MyDrive/Ex4Files/model_loss_history")  # TODO: you can change the path here


def get_config():
    sweep_config = {}
    sweep_config['method'] = 'random'
    sweep_config['metric'] = {'name': 'loss', 'goal': 'minimize'}

    sweep_config['name'] = f"BioEx4_{get_time()}"
    param_dict = {
        'RESNET_1_BLOCKS': {'distribution': 'int_uniform', 'min': 1, 'max': 10},
        'RESNET_1_KERNEL_SIZE': {'distribution': 'int_uniform', 'min': 1, 'max': 10},
        'RESNET_1_KERNEL_NUM': {'distribution': 'int_uniform', 'min': 5, 'max': 100},
        'RESNET_2_BLOCKS': {'distribution': 'int_uniform', 'min': 1, 'max': 10},
        'RESNET_2_KERNEL_SIZE': {'distribution': 'int_uniform', 'min': 1, 'max': 10},
        'RESNET_2_KERNEL_NUM': {'distribution': 'int_uniform', 'min': 5, 'max': 100},
        'DROPOUT': {'distribution': 'uniform', 'min': 0.001, 'max': 0.5},
        'EPOCHS': {'distribution': 'int_uniform', 'min': 2, 'max': 30},
        "LR": {'distribution': 'uniform', 'min': 0.001, 'max': 0.05},
        'BATCH': {'values': [16, 32, 64, 128, 256]}
    }

    for i in range(WANTED_M):
        param_dict[f"DILATION_{i}"] = {'distribution': 'int_uniform', 'min': 1, 'max': 5}

    sweep_config['parameters'] = param_dict
    return sweep_config


def get_default_config():
    sweep_config = {
        'RESNET_1_BLOCKS': RESNET_1_BLOCKS,
        'RESNET_1_KERNEL_SIZE': RESNET_1_KERNEL_SIZE,
        'RESNET_1_KERNEL_NUM': RESNET_1_KERNEL_NUM,
        'RESNET_2_BLOCKS': RESNET_2_BLOCKS,
        'RESNET_2_KERNEL_SIZE': RESNET_2_KERNEL_SIZE,
        'RESNET_2_KERNEL_NUM': RESNET_2_KERNEL_NUM,
        'DROPOUT': DROPOUT,
        'EPOCHS': EPOCHS,
        "LR": LR,
        'BATCH': BATCH
    }
    sweep_config['method'] = 'random'
    sweep_config['metric'] = {'name': 'loss', 'goal': 'minimize'}

    sweep_config['name'] = f"BioEx4_{get_time()}"

    for i in range(WANTED_M):
        sweep_config[f"DILATION_{i}"] = DILATION[i]

    return sweep_config


def train(config=None):
    if config is None:
        config = get_default_config()
    with wandb.init(config=config):

        # __________________________________________loading the data__________________________________________
        config = wandb.config
        input = np.load("train_input.npy")  # numpy array of shape (1974,NB_MAX_LENGTH,FEATURE_NUM) - data
        labels = np.load("train_labels.npy")  # numpy array of shape (1974,NB_MAX_LENGTH,OUTPUT_SIZE) - labels
        save_dir = "BestFits/"
        model_name = "test"
        fold_var = 1
        kf = KFold(n_splits=5)
        my_optimizer = tf.keras.optimizers.Adam(learning_rate=config['LR'])
        loss = np.zeros(5)

        for t_idx, v_idx in kf.split(input, labels):
            X_t, X_v = input[t_idx], input[v_idx]
            y_t, y_v = labels[t_idx], labels[v_idx]

            model = build_network(config)
            # ____________________________________________compiling___________________________________________

            model.compile(optimizer=my_optimizer, loss='mean_squared_error')

            # ________________________________________creating callbacks______________________________________
            checkpoint = tf.keras.callbacks.ModelCheckpoint(f"{save_dir}"
                                                            f"{model_name}"
                                                            f"{fold_var}.ckpt",
                                                            monitor='val_loss',
                                                            save_best_only=True, mode='max')
            callbacks_list = [checkpoint]

            # ________________________________________fitting the model_______________________________________
            history = model.fit(X_t, y_t,
                                epochs=config['EPOCHS'],
                                callbacks=callbacks_list,
                                batch_size=config['BATCH'],
                                validation_data=(X_v, y_v))

            #TODO decide how we want to save model here

            best_model = tf.keras.models.load_model(f"{save_dir}"
                                                    f"{model_name}"
                                                    f"{fold_var}.ckpt")
            loss[fold_var - 1] = best_model.evaluate(X_v, y_v)
            fold_var += 1
            tf.keras.backend.clear_session()

        wandb.log({'loss':np.mean(loss),"std":np.std(loss)})


def main():
    # sweep_id = wandb.sweep(get_config(), project="BioEx4",
    #                        entity="avishai-elma")
    # wandb.agent(sweep_id, train, count=1)
    train()


if __name__ == '__main__':
    train()
    # input_layer = tf.keras.Input(shape=(utils.NB_MAX_LENGTH, utils.FEATURE_NUM))
    #
    # # Conv1D -> shape = (NB_MAX_LENGTH, RESNET_1_KERNEL_NUM)
    # conv1d_layer = layers.Conv1D(config['RESNET_1_KERNEL_NUM'], config['RESNET_1_KERNEL_SIZE'],
    #                              padding='same')(input_layer)
    # dense = layers.Dense(15)(conv1d_layer)
    #
    # model = tf.model(input_layer,dense)
    # my_optimizer = tf.keras.optimizers.Adam(learning_rate=0.01)

