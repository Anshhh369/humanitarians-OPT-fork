# Import necessary libraries and modules

import os
import streamlit as st
import pinecone
from openai import OpenAI 
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain_openai import ChatOpenAI
from pinecone import Pinecone, PodSpec
from langchain_pinecone import PineconeVectorStore
from langchain_community.chat_models import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.prompts import PromptTemplate
from docx import Document
from io import StringIO
import PyPDF2
import docx

# Set up the environment

# Load secret keys
secrets = st.secrets
openai_api_key = secrets["openai"]["api_key"] # Access OpenAI API key
os.environ["OPENAI_API_KEY"] = openai_api_key

pinecone_api_key = secrets["pinecone"]["api_key"] # Access Pinecone API key
os.environ["PINECONE_API_KEY"] = pinecone_api_key



# text_splitter_module.py
class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, text):
        # Split the text into smaller documents based on chunk_size and chunk_overlap
        documents = []
        start_idx = 0
        while start_idx < len(text):
            end_idx = min(start_idx + self.chunk_size, len(text))
            documents.append(text[start_idx:end_idx])
            start_idx += self.chunk_size - self.chunk_overlap
        return documents


# Function to extract text from DOCX file
def extract_text_from_docx(uploaded_file):
    doc = docx.Document(uploaded_file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Function to extract text from PDF file
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfFileReader(uploaded_file)
    full_text = []
    for page_num in range(pdf_reader.numPages):
        page = pdf_reader.getPage(page_num)
        full_text.append(page.extractText())
    return '\n'.join(full_text)


st.title("Document Splitter")

# File uploader for user to upload a document
uploaded_file = st.file_uploader("Upload your document", type=["docx", "pdf"])

if uploaded_file is not None:
    # Extract text from the uploaded file based on its format
    if uploaded_file.type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':  # DOCX
        file_contents = extract_text_from_docx(uploaded_file)
    elif uploaded_file.type == 'application/pdf':  # PDF
        file_contents = extract_text_from_pdf(uploaded_file)
    else:
        st.write("Unsupported file format. Please upload a DOCX or PDF file.")
        st.stop()
    
    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter()
    
    split_docs = text_splitter.split_documents(file_contents)
    
    # Assuming each document is represented as a dictionary with 'page_content' key
    documents_with_metadata = [{'page_content': doc} for doc in split_docs]
    
    # Display the number of documents
    st.write(f"Number of documents: {len(split_docs)}")
    
    # Display each document
    for i, document in enumerate(split_docs):
        st.write(f"Document {i+1}:")
        st.write(document)



    
    # Embed the documents

    embeddings_model = OpenAIEmbeddings(openai_api_key=openai_api_key)

    # Create a new Pinecone Index and setup the vector database and search engine
    
    index_name = "langchain-demo"
    global index
    index = PineconeVectorStore.from_documents(documents_with_metadata, embeddings_model, index_name=index_name)

    # Define a function to find similar documents based on a given query

    def get_similiar_docs(query, k=1, score=False):
        if score:
            similar_docs = index.similarity_search_with_score(query, k=k)
        else:
            similar_docs = index.similarity_search(query, k=k)
        return similar_docs

    # Creating the Prompt
    question = st.text_input("Ask your question here")

    if st.button("Get Answer"):
            # Creating the Prompt
            template = """
            Answer the question in your own words from the context given to you.
            If questions are asked where there is no relevant context available, please answer from what you know.

            Context: {context}

            Human: {question}
            Assistant:

            """
            prompt = PromptTemplate(input_variables=["context", "question"], template=template)

            # Assigning the OPENAI model and Retrieval chain
            model_name = "gpt-4"
            llm = ChatOpenAI(model_name=model_name)

            # Define the Retrieval chain
            chain = RetrievalQA.from_chain_type(llm, retriever=index.as_retriever(), chain_type_kwargs={'prompt': prompt})

            # Get similar documents
            similar_docs = get_similar_docs(question)

            # Display similar documents
            st.write("Similar Documents:")
            for doc in similar_docs:
                st.write(doc)
            
# template = """
# Answer the question in your own words from the context given to you.
# If questions are asked where there is no relevant context available, please answer from what you know.

# Context: {context}

# Human: {question}
# Assistant:

# """

# prompt = PromptTemplate(
#     input_variables=["context", "question"], template=template
# )

# # Assigning the OPENAI model and Retrieval chain

# model_name = "gpt-4"
# llm = ChatOpenAI(model_name=model_name)

# chain = RetrievalQA.from_chain_type(llm, retriever=index.as_retriever(),chain_type_kwargs={'prompt': prompt}
#     )

# # Define Response Function

# def get_answer(query):
#     similar_docs = get_similiar_docs(query)
#     answer = chain({"query":query})
#     return answer

# # Streamlit Application

# st.title("Streamlit Langchain Application")

# question_input = st.text_input("Ask your question here:")

# if st.button("Get Answer"):
#     answer = get_answer(question_input)
#     st.write("Answer:", answer)


# File upload
# uploaded_file = st.file_uploader("Upload your file")

# if uploaded_file is not None:
#     # Process the uploaded file
#     file_contents = uploaded_file.read()
#     st.write("File contents:", file_contents)

#     # Try decoding with different encodings until successful
#     encodings_to_try = ['utf-8', 'latin-1', 'iso-8859-1']  # Add more encodings if needed
#     decoded_content = None
#     for encoding in encodings_to_try:
#         try:
#             decoded_content = file_contents.decode(encoding)
#             break  # Break out of loop if decoding is successful
#         except UnicodeDecodeError:
#             continue  # Try next encoding if decoding fails
    
#     if decoded_content is None:
#         st.write("Unable to decode file contents with any of the specified encodings.")
#     else:
#         # Call the function or method to split decoded_content into pages
#         pages = decoded_content.load_and_split()
    
#     #Split the documents into smaller chunks for processing
#     chunk_size=1000 
#     chunk_overlap=200
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
#     split_docs = text_splitter.split_documents(pages)

