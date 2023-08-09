

def set_intensity_susim( intensity):
    '''
    Function to ...
    '''
        intensity = int(intensity * 10)
        value = "{:04d}".format(intensity)
        message = "P=" + value
    return message.encode('utf-8')
