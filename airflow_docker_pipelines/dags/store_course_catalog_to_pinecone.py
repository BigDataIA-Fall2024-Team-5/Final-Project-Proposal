import os
from pinecone import Pinecone as PineconeClient, ServerlessSpec
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

# Initialize Pinecone client
pc = PineconeClient(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize NVIDIA embedding client
embedding_client = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    api_key=os.getenv("NVIDIA_API_KEY"),
    truncate="END"  # Adjust truncate settings based on model requirements
)

def create_index_in_pinecone(index_name="course-catalog-index"):
    """
    Create or reset the Pinecone index for course catalog data.
    """
    # Check and delete existing index
    if index_name in pc.list_indexes().names():
        print(f"Index '{index_name}' exists. Deleting...")
        pc.delete_index(index_name)
        print(f"Deleted existing index: {index_name}")

    # Create the index
    print(f"Creating Pinecone index: {index_name}...")
    pc.create_index(
        name=index_name,
        dimension=1024,
        metric="cosine", 
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print(f"Created new index: {index_name}")

    pinecone_index = pc.Index(index_name)
    # Connect to the index
    return pinecone_index

def add_course_data_to_index(pinecone_index, df):
    """
    Add course data to the Pinecone index.
    """
    print("Adding course data to Pinecone index...")

    for _, row in df.iterrows():
        try:
            # Prepare content for embedding
            chunk_content = (
                f"COURSE_NAME: {row['COURSE_NAME']}\n"
                f"DESCRIPTION: {row['DESCRIPTION']}\n"
            )

            # Generate embedding using NVIDIA API
            embedding = embedding_client.embed_query(chunk_content)

            # Metadata for the embedding
            metadata = {
                "course_code": row["COURSE_CODE"],
                "course_name": row["COURSE_NAME"],
                "description": row['DESCRIPTION'] or "No description available",
                "prerequisites": row['PREREQUISITES'] or "None",
                "corequisites": row['COREQUISITES'] or "None",
                "credits": row["CREDITS"],
                "subject_code": row["SUBJECT_CODE"],
            }

            # Upsert the data into Pinecone
            pinecone_index.upsert([
                {"id": row["COURSE_CODE"], "values": embedding, "metadata": metadata}
            ])
            print(f"Stored/updated embedding for course: {row['COURSE_CODE']}")
        except Exception as e:
            print(f"Error storing data for course {row['COURSE_CODE']}: {e}")

# Main logic for handling Pinecone indexing
def store_course_catalog_to_pinecone(df,name):
    """
    Handle the complete process of indexing course catalog data in Pinecone.
    """
    index_name = name
    pinecone_index = create_index_in_pinecone(index_name)
    add_course_data_to_index(pinecone_index, df)
    print(f"All course data indexed successfully in '{index_name}'.")
