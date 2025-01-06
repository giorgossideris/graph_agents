# graph_agents
This project aims to integrate the concepts of **multiagent systems** and **knowledge graphs** to create advanced query-answering capabilities. A multiagent system comprises multiple artificial intelligence agents collaborating to perform tasks for a user or another system, leveraging collective intelligence ([IBM](https://www.ibm.com/think/topics/multiagent-system)). Meanwhile, a knowledge graph is an organized representation of real-world entities and their interrelations, stored in a graph database that natively captures these connections ([Neo4j](https://neo4j.com/blog/what-is-knowledge-graph/)). By combining the specialized reasoning capabilities of multiagent systems with the structured semantic relationships of knowledge graphs, the approach seeks to enable **more accurate**, **context-aware**, and **scalable** solutions for **complex query answering**.

*Of course, the goal is not to create a thoroughly tested production system, but rather a simple implementation designed to showcase the intended functionality.*

## Acknowledgements
Three resources influenced the implementation:
* [GraphRag: Getting Started](https://microsoft.github.io/graphrag/get_started/)
* [Commit cb0aae7 in GraphRAG](https://github.com/microsoft/graphrag/commit/cb0aae7e6bf1763ca5a7540d2220c11162863915)
* [Knowledge Graphs for RAG course by DeepLearning.AI](https://learn.deeplearning.ai/courses/knowledge-graphs-rag)

## The process
The specific implementation consists of 3 steps:
1. Creation of the knowledge graph: this is done with [GraphRAG](https://github.com/microsoft/graphrag).
2. Saving the graph in a database: a [Neo4j](https://neo4j.com/) graph database is used.
3. Building the multiagent system for question answering: [using AG2](https://github.com/ag2ai/ag2) (formerly AutoGen).

### 1. Creation of the knowledge graph
GraphRag refers to this process as indexing, which is designed to extract entities, relationships, and claims from raw text, perform community detection among entities, and generate community summaries and reports at various levels of granularity. Additionally, it embeds entities into a graph vector space and text chunks into a textual vector space. You can find more information [here](https://microsoft.github.io/graphrag/index/overview/).

### 2. Saving the graph in a database
A powerful database option for graphs is Neo4j. It uses nodes, relationships, and properties to represent and store data, enabling highly efficient querying and analysis of complex, interconnected information. You can find more information [here](https://neo4j.com/product/neo4j-graph-database/).

### 3. Building the multiagent system for question answering
The multiagent system will be built with AG2 (formerly AutoGen). The architecture will be the following: 
![image](https://github.com/user-attachments/assets/ed4d6663-1b48-4ddb-827d-dfe198bbda3a)

* The **Graph Agent** is responsible for querying the graph database to collect the necessary information.
* The **Entities Agent** identifies entities that are related to the given input.
* The **Orchestrator** interacts with the other two agents in order to collect the required information and return it to the user.

## Files
* `pipeline.ipynb`: includes the main logic and the pipeline of the 3 steps described above.
* `neo4j_loading.py`: includes the code for loading the graph database, with the data (it is imported within `pipeline.ipynb`).
* `neo4j_config.json`: includes the Neo4j credentials (**must be filled before running the pipeline**)
* `openai_config.json`: includes the OpenAI credentials (**must be filled before running the pipeline**)
* `requirements.txt`: the requirements file for this project.

