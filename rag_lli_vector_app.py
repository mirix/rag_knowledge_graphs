import os
n_cores = os.cpu_count()
os.environ['OMP_NUM_THREADS'] = str(n_cores)
os.environ['MKL_NUM_THREADS'] = str(n_cores)
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="1,0"

from flask import Flask, render_template, request

from ctransformers import AutoModelForCausalLM
from transformers import AutoTokenizer

from llama_index import (ServiceContext,
                         VectorStoreIndex,
                         set_global_service_context,
                         SimpleDirectoryReader)

from llama_index.llms import HuggingFaceLLM
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index.prompts import PromptTemplate

### APP ###

# An example prompt that works
# prompt = "What are leverage ratios?"

app = Flask(__name__)
app.static_folder = 'static'

@app.route('/')
def home():
	return render_template('index.html')

### MODEL ###

name = 'allenai/tulu-2-dpo-13b'

model_name = 'TheBloke/tulu-2-dpo-13B-GGUF'
#model_file = 'solar-10.7b-instruct-v1.0.Q4_K_M.gguf'
model_file = 'tulu-2-dpo-13b.Q8_0.gguf'

model = AutoModelForCausalLM.from_pretrained(model_name, model_file=model_file, context_length=4096, gpu_layers=512, hf=True)
											
tokenizer = AutoTokenizer.from_pretrained(name)

system_prompt = 'Please, check if the anwser can be inferred from the pieces of context provided. If the answer cannot be inferred from the context, just state that the question is out of scope and do not provide any answer.'
prompt_template = '<|system|>\n' + system_prompt + '</s>\n<|user|>\n{query_str}</s>\n<|assistant|>\n'

llm = HuggingFaceLLM(
	model=model, 
	tokenizer=tokenizer, 
	query_wrapper_prompt=PromptTemplate(prompt_template),
	context_window=3072,
	max_new_tokens=256,
	tokenizer_kwargs={'max_length': 4096},
	model_kwargs={'n_gpu_layers': 200, 'n_threads': n_cores//2},
	#generate_kwargs={"temperature": 0.7},
	)

embed_model = HuggingFaceEmbedding(model_name='thenlper/gte-large')

### CONTEX ##

service_context = ServiceContext.from_defaults(
    chunk_size=256,
    llm=llm,
    embed_model=embed_model
)

set_global_service_context(service_context)

# Documents 

#documents = SimpleDirectoryReader(data_folder).load_data()
reader = SimpleDirectoryReader(input_dir='./pdf/')
documents = reader.load_data()
print('Number of pages:', len(documents))

# Vector Index

index = VectorStoreIndex.from_documents(documents)

### QUERY ###

query_engine = index.as_query_engine()

### APP FUNCTION ###

@app.route('/get')
def get_bot_response():
	
	try: msg
	except NameError: msg = ''
	
	query = request.args.get('msg')
	
	response = query_engine.query(query)
	print(response)
	
	return str(response)
	
if __name__ == '__main__':
   app.run(host = "0.0.0.0", port = 5000, debug = False)

