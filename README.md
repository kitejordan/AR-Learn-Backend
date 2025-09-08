# AR-Learn-Backend

Backend for AR-Learn, providing API endpoints and integrations with Neo4j and OpenAI.

## Features

- RESTful API for actions, health, and QA
- Neo4j graph database integration
- OpenAI API integration

## Getting Started

1. Copy `example.env` to `.env` and fill in your credentials.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app/main.py
   ```

## Project Structure

```
├── app/
│   ├── api/
│   │   ├── actions.py
│   │   ├── health.py
│   │   └── qa.py
│   ├── clients/
│   │   ├── neo4j_client.py
│   │   └── openai_client.py
│   ├── config/
│   │   └── settings.py
│   ├── dtos/
│   │   ├── actions.py
│   │   └── qa.py
│   ├── managers/
│   │   ├── action_manager.py
│   │   ├── graph_manager.py
│   │   └── narration_manager.py
│   └── main.py
├── scripts/
│   └── seed_neo4j.py
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── README.md
└── example.env
```


## Our Contributors

<div align = "center">
 <h3>Thank you for contributing to our repository.😃</h3>
<a href="https://github.com/kitejordan/AR-Learn-Backend/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=kitejordan/AR-Learn-Backend" />
</a>
<div>
