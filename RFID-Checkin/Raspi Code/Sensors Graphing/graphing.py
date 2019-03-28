import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import sensors

# Create figure for plotting
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
xs = []
ys = []

# Initialize communication with sensors
sensors.setup()

# This function is called periodically from FuncAnimation
def animate(i, xs, ys):
    dist_cm = sensors.get_sensor_value(0)
    # Add x and y to lists
    xs.append(datetime.datetime.now())
    ys.append(dist_cm)
    # Draw x and y lists
    ax.clear()
    ax.plot(xs, ys)
    # Format plot
    #plt.xticks(rotation=45, ha='right')
    #plt.subplots_adjust(bottom=0.30)
    plt.title('HCSR04 Distance over Time')
    plt.ylabel('Distance (cm)')

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=1)
plt.show()
