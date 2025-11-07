# BodhiRAG Deployment

This directory contains all deployment configurations and scripts for BodhiRAG.

## Quick Start

### Deploy to Hugging Face Spaces

```bash
# Windows
set HF_TOKEN=your_token_here
deploy.bat

# Or manually
python huggingface_deploy.py --token %HF_TOKEN%
```

### Deploy with Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access at http://localhost:7860
```

## Files

- **huggingface_deploy.py** - Main deployment script
- **deploy.bat** - Windows quick deploy script
- **DEPLOYMENT_GUIDE.md** - Complete deployment documentation
- **MODEL_CARD.md** - Model card for Hugging Face
- **Dockerfile** - Docker container configuration
- **docker-compose.yml** - Multi-container setup with Neo4j
- **hf_space/** - Generated Hugging Face Space files

## Deployment Options

### 1. Hugging Face Spaces (Recommended)

**Pros:**
- Free tier available
- Easy to share
- Automatic scaling
- Built-in CI/CD

**Cons:**
- Requires external Neo4j
- Limited compute on free tier

**Setup:**
1. Get HF token from https://huggingface.co/settings/tokens
2. Run `deploy.bat` or `huggingface_deploy.py`
3. Configure environment variables in Space settings
4. Wait for build to complete

### 2. Docker Deployment

**Pros:**
- Complete control
- Includes Neo4j
- Easy local testing
- Portable

**Cons:**
- Requires Docker
- Manual scaling
- More maintenance

**Setup:**
```bash
docker-compose up -d
```

### 3. Manual Deployment

**Pros:**
- Maximum flexibility
- Custom configuration
- Any hosting provider

**Cons:**
- More complex
- Manual updates
- Requires expertise

**Setup:**
See DEPLOYMENT_GUIDE.md for detailed instructions

## Environment Variables

Required for all deployments:

```
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

Optional:

```
HF_TOKEN=your-hf-token (for deployment only)
LLM_ENDPOINT=your-llm-api (for production)
LLM_API_KEY=your-api-key (for production)
```

## Testing Your Deployment

### Local Testing

```bash
# Test with mock data
python deployment/hf_space/app.py

# Access at http://localhost:7860
```

### Production Testing

1. **Health Check**: Verify Space is running
2. **Basic Query**: Test simple question
3. **KG Test**: Query with relationships
4. **Vector Test**: Query for descriptions
5. **Source Check**: Verify citations

## Monitoring

### Hugging Face Spaces

- Check Space logs in HF dashboard
- Monitor build status
- View usage analytics

### Docker

```bash
# View logs
docker-compose logs -f bodhirag

# Check status
docker-compose ps

# Restart services
docker-compose restart
```

## Troubleshooting

### Common Issues

1. **Build Fails**
   - Check requirements.txt versions
   - Verify Python version (3.11+)
   - Check logs for specific errors

2. **Neo4j Connection Error**
   - Verify URI format: `bolt://host:7687`
   - Check credentials
   - Ensure Neo4j is running

3. **ChromaDB Error**
   - Check file permissions
   - Verify data directory exists
   - Clear cache and rebuild

4. **Slow Performance**
   - Upgrade to paid tier
   - Optimize queries
   - Add caching

See DEPLOYMENT_GUIDE.md for detailed troubleshooting.

## Updating Deployment

### Hugging Face

```bash
# Make changes
# Test locally
# Re-run deployment
python huggingface_deploy.py --token %HF_TOKEN%
```

### Docker

```bash
# Rebuild containers
docker-compose down
docker-compose build
docker-compose up -d
```

## Cost Estimates

### Free Tier
- HF Spaces: Free (CPU)
- Neo4j AuraDB: Free tier
- Total: $0/month

### Production
- HF Spaces: $0-50/month
- Neo4j AuraDB: $65+/month
- Total: $65+/month

## Support

- **Documentation**: See DEPLOYMENT_GUIDE.md
- **Issues**: Open GitHub issue
- **Questions**: HF Space discussions

## License

MIT License - See LICENSE file

---

**B