import re
import matplotlib.pyplot as plt

# Function to extract data from file
def extract_losses_from_file(file_path):
    with open(file_path, 'r') as file:
        log = file.read()

    test_losses = []

    for match in re.finditer(r"step 9500 train loss: ([\d.]+) test loss: ([\d.]+)", log):
        test_losses.append(float(match.group(2)))

    return test_losses

epochs_num = 40

# Plot losses
def plot_test_losses(file1_test_losses,  file2_test_losses):
    plt.figure(figsize=(10, 6))
    plt.plot(list(range(1,epochs_num+1)), file1_test_losses[:epochs_num], label="Transformer Test Loss", marker='x')
    plt.plot(list(range(1,epochs_num+1)), file2_test_losses[:epochs_num], label="RotaryTransformer Test Loss", marker='o')
    plt.xlabel("Epochs")
    plt.ylabel("Test Loss")
    plt.legend()
    plt.grid(True)
    plt.show()

# Main function
if __name__ == "__main__":
    # file1_path = "checkpoint/transformerC4free/utumshrrxq/train.log"  # Replace with your first file path
    # file2_path = "checkpoint/RotaryTransformerK3free/xrlsx2o7d9/train.log"  # Replace with your second file path
# checkpoint\RotaryTransformerK3free\xrlsx2o7d9\train.log
# checkpoint/transformerK3free/utumshrrxq/train.log

# checkpoint\RotarytransformerC4free\egu6cbrbfg\train.log
# checkpoint\transformerC4free\nqngm89dnh\train.log
    file1_path = "checkpoint/transformerC4free/nqngm89dnh/train.log"  # Replace with your first file path
    file2_path = "checkpoint/RotarytransformerC4free/egu6cbrbfg/train.log"  # Replace with your second file path
    file1_test_losses = extract_losses_from_file(file1_path)
    file2_test_losses = extract_losses_from_file(file2_path)
    plot_test_losses(file1_test_losses,  file2_test_losses)
