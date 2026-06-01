import js


def acc_read():
    """
    Returns current x, y, z accelerations in m/s**2.
    """
    a = js.getAccelerometerData()
    return (float(a[0]), float(a[1]), float(a[2]))


def gyro_read():
    """
    Returns current x, y, z rotation rate in degrees/s.
    """
    g = js.getGyroscopeData()
    return (float(g[0]), float(g[1]), float(g[2]))


def pressure_read():
    """
    Returns current pressure in Pa and temperature in degree C.
    """
    return (7.0, 8.0)


def step_counter_read():
    return 1337
