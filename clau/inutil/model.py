from transformers import AutoProcessor, LlavaForConditionalGeneration
from PIL import Image
import torch

# Load model and processor
model_id = "llava-hf/llava-1.5-7b-hf"
processor = AutoProcessor.from_pretrained(model_id)
model = LlavaForConditionalGeneration.from_pretrained(
    model_id, torch_dtype=torch.float16, low_cpu_mem_usage=True
).to("cuda" if torch.cuda.is_available() else "cpu")

# Load image and prompt
# Get the absolute path to the script's directory
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "pantalla_control.jpeg")
print(f"Looking for image at: {image_path}")

# Try to open the image
try:
    image = Image.open(image_path)
except FileNotFoundError:
    # List files in the directory to help debug
    print(f"Files in {script_dir}:")
    for file in os.listdir(script_dir):
        print(f"  - {file}")
    raise
prompt = "<image>\nDescribe in detail everything visible in this image."

# Process inputs
inputs = processor(text=prompt, images=image, return_tensors="pt")  # Using named parameters
inputs = {k: v.to(model.device) for k, v in inputs.items()}

# Generate response
with torch.inference_mode():
    generate_ids = model.generate(**inputs, max_new_tokens=512)
    
output = processor.batch_decode(generate_ids, skip_special_tokens=True)[0]
print("🧠 LLaVA output:")
print(output)