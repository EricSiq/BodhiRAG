# BodhiRAG Hugging Face Deployment Guide

Complete guide to deploying BodhiRAG to Hugging Face Spaces.

## Prerequisites

1. **Hugging Face Account**: Create account at https://huggingface.co
2. **Hugging Face Token**: Get from https://huggingface.co/settings/tokens
3. **Neo4j Database**: Set up Neo4j instance (AuraDB or self-hosted)
4. **Python Environment**: Python 3.11+ with dependencies installed

## Quick Start

### Option 1: Automated Deployment

```bash
# Set your Hugging Face token
set HF_TOKEN=hf_your_token_here
# Run deployment script
python deployment/huggingface_deploy.py --token %HF_TOKEN% --repo-name your-space-name
```

### Option 2: Manual Deployment

1. **Prepare Files**:
```bash
python deployment/huggingface_deploy.py --prepare-only
```

2. **Review Generated Files** in `deployment/hf_space/`:
   - `app.py` - Gradio interface
   - `requirements.txt` - Dependencies
   - `README.md` - Space documentation
   - `src/` - Model code

3. **Create Space on Hugging Face**:
   - Go to https://huggingface.co/new-space
   - Choose "Gradio" SDK
   - Name your space (e.g., `bodhirag-space-biology`)

4. **Upload Files**:
```bash
# Clone your space
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# Copy deployment files
xcopy /E /I ..\BodhiRAG-main\deployment\hf_space\* .

# Commit and push
git add .
git commit -m "Initial deployment"
git push
```

## Configuration

### Environment Variables

Set these in your Hugging Face Space settings:

```
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

### Neo4j Setup Options

#### Option A: Neo4j AuraDB (Recommended for Production)

1. Go to https://neo4j.com/cloud/aura/
2. Create free instance
3. Save connection URI and credentials
4. Add to HF Space environment variables

#### Option B: Self-Hosted Neo4j

1. Deploy Neo4j on cloud provider (AWS, GCP, Azure)
2. Configure security and networking
3. Use public endpoint in HF Space

#### Option C: Development Mode (Mock Data)

For testing without Neo4j:
- Leave environment variables empty
- System will use mock data
- Limited functionality

## Deployment Architecture

```
┌─────────────────────────────────────┐
│   Hugging Face Space (Gradio)      │
│                                     │
│  ┌──────────────────────────────┐  │
│  │      app.py (Frontend)       │  │
│  └──────────────────────────────┘  │
│              ↓                      │
│  ┌──────────────────────────────┐  │
│  │   HybridRAGAgent (Router)    │  │
│  └──────────────────────────────┘  │
│         ↓              ↓            │
│  ┌──────────┐   ┌──────────────┐  │
│  │ Neo4j KG │   │ ChromaDB VS  │  │
│  │(External)│   │  (Embedded)  │  │
│  └──────────┘   └──────────────┘  │
└─────────────────────────────────────┘
```

## Features in Deployed Space

### 1. Interactive Query Interface
- Natural language questions
- Toggle KG/Vector retrieval
- Real-time results

### 2. Knowledge Graph Exploration
- View entity relationships
- See evidence from papers
- Multi-hop reasoning

### 3. Semantic Search
- Find relevant documents
- Similarity scoring
- Source attribution

### 4. Hybrid RAG
- Automatic query routing
- Combined KG + Vector results
- Explainable answers

## Testing Your Deployment

### Example Queries

1. **Relationship Query** (KG Primary):
   ```
   What causes bone loss in space?
   ```

2. **Descriptive Query** (Vector Primary):
   ```
   Describe oxidative stress in microgravity
   ```

3. **Complex Query** (Hybrid):
   ```
   How does radiation affect DNA and what countermeasures exist?
   ```

### Verification Steps

1. **Check Space Status**: Ensure "Running" status on HF
2. **Test Basic Query**: Try simple question
3. **Verify KG Connection**: Check relationship results
4. **Verify Vector Search**: Check document retrieval
5. **Check Sources**: Verify citations appear

## Troubleshooting

### Common Issues

#### 1. Space Build Fails
- **Cause**: Dependency conflicts
- **Fix**: Check `requirements.txt` versions
- **Solution**: Pin compatible versions

#### 2. Neo4j Connection Error
- **Cause**: Wrong credentials or URI
- **Fix**: Verify environment variables
- **Solution**: Test connection separately

#### 3. ChromaDB Initialization Error
- **Cause**: Missing data or permissions
- **Fix**: Check file system permissions
- **Solution**: Rebuild vector store

#### 4. Slow Response Times
- **Cause**: Cold start or large queries
- **Fix**: Optimize query complexity
- **Solution**: Add caching layer

### Debug Mode

Enable debug logging in `app.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Optimization

### 1. Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(query: str):
    return agent.route_query(query, True, True)
```

### 2. Batch Processing
- Pre-compute common queries
- Cache frequent results
- Use connection pooling

### 3. Resource Management
- Limit concurrent connections
- Set query timeouts
- Monitor memory usage

## Scaling Considerations

### For Production Use

1. **Database Scaling**:
   - Use Neo4j Enterprise
   - Enable clustering
   - Add read replicas

2. **Vector Store Optimization**:
   - Use persistent storage
   - Enable compression
   - Optimize embeddings

3. **API Rate Limiting**:
   - Add request throttling
   - Implement queue system
   - Monitor usage

4. **Monitoring**:
   - Add logging
   - Track metrics
   - Set up alerts

## Cost Estimation

### Free Tier (Development)
- HF Space: Free (CPU)
- Neo4j AuraDB: Free tier available
- ChromaDB: Embedded (no cost)
- **Total**: $0/month

### Production Tier
- HF Space: $0-50/month (depending on usage)
- Neo4j AuraDB: $65+/month
- Cloud hosting: $50+/month
- **Total**: $115+/month

## Security Best Practices

1. **Never commit credentials** to git
2. **Use environment variables** for secrets
3. **Enable Neo4j authentication**
4. **Use HTTPS** for all connections
5. **Implement rate limiting**
6. **Monitor access logs**

## Updating Your Deployment

### Code Updates

```bash
# Make changes locally
# Test changes

# Push to HF Space
cd YOUR_SPACE_NAME
git pull origin main
# Copy updated files
git add .
git commit -m "Update: description"
git push
```

### Data Updates

1. **Update Knowledge Graph**:
   - Run pipeline with new data
   - Merge into existing graph
   - Verify relationships

2. **Update Vector Store**:
   - Re-embed new documents
   - Add to collection
   - Rebuild index if needed

## Alternative Deployment Options

### 1. Hugging Face Inference Endpoints
- More control over resources
- Better for production
- Higher cost

### 2. Docker Container
- Full control
- Deploy anywhere
- More complex setup

### 3. Cloud Functions
- Serverless option
- Pay per use
- Cold start issues

## Support and Resources

- **Hugging Face Docs**: https://huggingface.co/docs/hub/spaces
- **Neo4j Docs**: https://neo4j.com/docs/
- **ChromaDB Docs**: https://docs.trychroma.com/
- **Gradio Docs**: https://gradio.app/docs/

## Next Steps

1. ✅ Deploy to Hugging Face
2. ✅ Configure environment variables
3. ✅ Test basic functionality
4. 📊 Add analytics and monitoring
5. 🚀 Share with community
6. 📈 Scale based on usage

## License

MIT License - See LICENSE file for details

---

**Built for NASA Space Apps Challenge 2025**
