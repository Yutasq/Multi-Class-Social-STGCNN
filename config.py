annotationType="stanford"
labels=["Biker","Pedestrian","Car","Bus","Skater","Cart"]
path="stanfordProcessed"
samplingRate=10
epochs=300
fractionToRemove=10
checkpoint="checkpoint\\stanfordProcessed-10\\Biker-Pedestrian-Car-Bus-Skater-Cart"
one_hot_encoding = {}
for i in range(len(labels)):
    encoding = [0.] * len(labels)
    encoding[len(labels) - 1 - i] = 1.
    one_hot_encoding[labels[i]] = encoding
outlierValue=10000

class_enc=True
class_weighting=True