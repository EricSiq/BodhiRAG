# 🚀 BodhiRAG Hugging Face Deployment

Complete guide to deploying your BodhiRAG model to Hugging Face Spaces.

## 📋 Overview

BodhiRAG is now ready for deployment to Hugging Face! This deployment includes:

- ✅ **Gradio Interface** - Interactive web UI for querying
- ✅ **Hybrid RAG Agent** - Intelligent query routing
- ✅ **Knowledge Graph** - Neo4j integration for relationships
- ✅ **Vector Store** - ChromaDB for semantic search
- ✅ **Model Card** - Complete documentation
- ✅ **Docker Support** - Alternative deployment option

## 🎯 Quick Start (3 Steps)

### Step 1: Get Hugging Face Token

1. Go to https://huggingface.co/settings/tokens
2. Create a new token with "write" access
3. Copy the token

### Step 2: Set Environment Variable

```cmd
set HF_TOKEN=hf_your_token_here
```

### Step 3: Deploy

```cmd
cd BodhiRAG-main
deployment\deploy.bat
```

That's it! Your model will be deployed to Hugging Face Spaces.

## 📁 What Was Created

### Deployment Files

```
deployment/
├── huggingface_deploy.py    # Main deployment script
├── deploy.bat                # Windows quick deploy
├── test_deployment.py        # Pre-deployment tests
├── DEPLOYMENT_GUIDE.md       # Detailed documentation
├── MODEL_CARD.md             # Model card for HF
├── Dockerfile                # Docker container
├── docker-compose.yml        # Multi-container setup
└── hf_space/                 # Generated HF Space files
    ├── app.py                # Gradio interface
    ├── requirements.txt      # Dependencies
    ├── README.md             # Space documentation
    └── src/                  # Model code
```

### Key Components

#### 1. Gradio App (`hf_space/app.py`)

Interactive web interface with:
- Natural language query input
- Toggle for KG/Vector retrieval
- Real-time results display
- Example queries
- Source attribution

#### 2. Deployment Script (`huggingface_deploy.py`)

Automated deployment with:
- File preparation
- Space creation
- File upload
- Configuration

#### 3. Model Card (`MODEL_CARD.md`)

Complete documentation including:
- Model description
- Use cases
- Limitations
- Training details
- Evaluation metrics

## 🔧 Configuration

### Required Environment Variables

Set these in your Hugging Face Space settings:

```
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-secure-password
```

### Neo4j Setup Options

#### Option A: Neo4j AuraDB (Recommended)

1. Go to https://neo4j.com/cloud/aura/
2. Create free instance
3. Save credentials
4. Add to HF Space settings

#### Option B: Development Mode

- Leave environment variables empty
- System uses mock data
- Limited functionality

## 🧪 Testing Before Deployment

Run pre-deployment tests:

```cmd
python deployment\test_deployment.py
```

This validates:
- ✓ All imports work
- ✓ Connectors initialize
- ✓ Agent functions
- ✓ Deployment files exist
- ✓ Mock queries work

## 📊 Deployment Options

### Option 1: Automated (Recommended)

```cmd
deployment\deploy.bat
```

**Pros:**
- One command
- Automatic setup
- Error handling

### Option 2: Manual

```cmd
python deployment\huggingface_deploy.py --token %HF_TOKEN% --repo-name your-space-name
```

**Pros:**
- More control
- Custom repo name
- Step-by-step

### Option 3: Prepare Only

```cmd
python deployment\huggingface_deploy.py --prepare-only
```

**Pros:**
- Review files first
- Manual upload
- Full control

### Option 4: Docker

```cmd
docker-compose -f deployment\docker-compose.yml up -d
```

**Pros:**
- Local testing
- Includes Neo4j
- Complete stack

## 🎨 Customization

### Change Space Name

```cmd
python deployment\huggingface_deploy.py --repo-name my-custom-name
```

### Modify Interface

Edit `deployment/hf_space/app.py`:

```python
# Change title
gr.Blocks(title="My Custom Title")

# Add custom examples
examples = [
    ["Your custom query", True, True],
]

# Modify theme
gr.themes.Soft()  # or Base(), Glass(), etc.
```

### Update Model Card

Edit `deployment/MODEL_CARD.md` with your:
- Team information
- Custom metrics
- Additional use cases
- Citations

## 📈 After Deployment

### 1. Configure Space

1. Go to your Space on Hugging Face
2. Click "Settings"
3. Add environment variables:
   - `NEO4J_URI`
   - `NEO4J_USERNAME`
   - `NEO4J_PASSWORD`
4. Save settings

### 2. Wait for Build

- Space will automatically build
- Check logs for errors
- Usually takes 2-5 minutes

### 3. Test Your Space

Try these queries:
- "What causes bone loss in space?"
- "How does microgravity affect muscle?"
- "Describe oxidative stress"

### 4. Share Your Space

- Get shareable link
- Embed in website
- Share on social media

## 🔍 Monitoring

### Check Space Status

```
https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
```

### View Logs

1. Go to Space page
2. Click "Logs" tab
3. Monitor real-time output

### Usage Analytics

- View in HF dashboard
- Track queries
- Monitor performance

## 🐛 Troubleshooting

### Build Fails

**Issue**: Space build fails

**Solutions:**
1. Check requirements.txt versions
2. Verify Python 3.11 compatibility
3. Review build logs
4. Test locally first

### Neo4j Connection Error

**Issue**: Can't connect to Neo4j

**Solutions:**
1. Verify URI format: `bolt://host:7687`
2. Check credentials
3. Ensure Neo4j is running
4. Test connection separately

### Slow Performance

**Issue**: Queries take too long

**Solutions:**
1. Upgrade to paid tier
2. Optimize queries
3. Add caching
4. Use smaller models

### Import Errors

**Issue**: Module not found

**Solutions:**
1. Check requirements.txt
2. Verify file structure
3. Test imports locally
4. Review logs

## 💰 Cost Estimates

### Free Tier
- **HF Space**: Free (CPU)
- **Neo4j AuraDB**: Free tier available
- **Total**: $0/month

### Production Tier
- **HF Space**: $0-50/month
- **Neo4j AuraDB**: $65+/month
- **Total**: $65+/month

## 🔐 Security

### Best Practices

1. ✅ Never commit credentials
2. ✅ Use environment variables
3. ✅ Enable Neo4j auth
4. ✅ Use HTTPS
5. ✅ Implement rate limiting
6. ✅ Monitor access logs

### Secrets Management

Store in HF Space settings:
- Database credentials
- API keys
- Tokens

Never in code:
- Passwords
- Connection strings
- Private keys

## 🚀 Advanced Features

### Add Authentication

```python
demo.launch(auth=("username", "password"))
```

### Enable Queue

```python
demo.queue()
demo.launch()
```

### Add Analytics

```python
import gradio as gr

def track_query(query):
    # Your analytics code
    pass
```

### Custom Domain

1. Upgrade to Pro
2. Configure DNS
3. Add custom domain in settings

## 📚 Resources

### Documentation
- [Hugging Face Spaces](https://huggingface.co/docs/hub/spaces)
- [Gradio Docs](https://gradio.app/docs/)
- [Neo4j Docs](https://neo4j.com/docs/)
- [ChromaDB Docs](https://docs.trychroma.com/)

### Support
- GitHub Issues
- HF Discussions
- Community Forums

### Examples
- [Example Spaces](https://huggingface.co/spaces)
- [Gradio Gallery](https://gradio.app/gallery/)

## 🎓 Next Steps

1. ✅ Deploy to Hugging Face
2. ✅ Configure environment
3. ✅ Test functionality
4. 📊 Add analytics
5. 🎨 Customize interface
6. 📈 Monitor usage
7. 🚀 Scale as needed
8. 🌟 Share with community

## 📝 Deployment Checklist

Before deploying:
- [ ] HF token obtained
- [ ] Neo4j instance ready
- [ ] Tests passing
- [ ] Files reviewed
- [ ] Model card updated

After deploying:
- [ ] Environment variables set
- [ ] Build successful
- [ ] Basic queries work
- [ ] Sources display
- [ ] Performance acceptable

## 🏆 Success Criteria

Your deployment is successful when:
- ✅ Space builds without errors
- ✅ Interface loads correctly
- ✅ Queries return results
- ✅ Sources are attributed
- ✅ Performance is acceptable

## 🤝 Contributing

To improve deployment:
1. Fork repository
2. Make improvements
3. Test thoroughly
4. Submit pull request

## 📄 License

MIT License - See LICENSE file

---

## 🎉 Congratulations!

You're now ready to deploy BodhiRAG to Hugging Face!

**Questions?** Check the [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) for detailed documentation.

**Issues?** Open a GitHub issue or ask in HF Discussions.

**Built for NASA Space Apps Challenge 2025** 🚀
