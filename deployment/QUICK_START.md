# 🚀 BodhiRAG - Quick Start Deployment Guide

## Deploy in 3 Steps (5 Minutes)

### Step 1️⃣: Get Hugging Face Token

1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name it "BodhiRAG Deploy"
4. Select "Write" access
5. Click "Generate"
6. Copy the token (starts with `hf_...`)

### Step 2️⃣: Set Token

Open Command Prompt and run:

```cmd
set HF_TOKEN=hf_your_token_here
```

Replace `hf_your_token_here` with your actual token.

### Step 3️⃣: Deploy

```cmd
cd BodhiRAG-main
deployment\deploy.bat
```

**That's it!** Your model is now deploying to Hugging Face! ✨

---

## What Happens Next?

### During Deployment (2-3 minutes)
- ✅ Files are prepared
- ✅ Space is created on Hugging Face
- ✅ Code is uploaded
- ✅ Dependencies are installed

### After Deployment (2-5 minutes)
- 🔨 Space builds automatically
- 🚀 App starts running
- 🌐 Your Space is live!

---

## Configure Your Space

### 1. Go to Your Space

```
https://huggingface.co/spaces/YOUR_USERNAME/bodhirag-space-biology
```

### 2. Click "Settings" Tab

### 3. Add Environment Variables

Click "New secret" and add:

**Secret 1:**
- Name: `NEO4J_URI`
- Value: `bolt://your-neo4j-instance:7687`

**Secret 2:**
- Name: `NEO4J_USERNAME`
- Value: `neo4j`

**Secret 3:**
- Name: `NEO4J_PASSWORD`
- Value: `your-password`

### 4. Save and Restart

Click "Save" and your Space will restart with the new configuration.

---

## Don't Have Neo4j?

### Option A: Use Free Neo4j AuraDB

1. Go to https://neo4j.com/cloud/aura/
2. Click "Start Free"
3. Create account
4. Create free instance
5. Copy connection details
6. Add to HF Space settings

### Option B: Use Mock Data (Testing)

- Skip Neo4j configuration
- System will use mock data
- Limited functionality
- Good for demos

---

## Test Your Deployment

### Try These Queries:

1. **"What causes bone loss in space?"**
   - Tests Knowledge Graph retrieval
   - Should show relationships

2. **"Describe oxidative stress in microgravity"**
   - Tests Vector Store search
   - Should show relevant documents

3. **"How does radiation affect DNA?"**
   - Tests Hybrid RAG
   - Should combine both sources

---

## Troubleshooting

### Build Failed?

**Check:**
- Python version (need 3.11+)
- Internet connection
- HF token is valid

**Fix:**
```cmd
python deployment\test_deployment.py
```

### Can't Connect to Neo4j?

**Check:**
- URI format: `bolt://host:7687`
- Username and password
- Neo4j is running

**Fix:**
- Use mock data mode (skip Neo4j config)
- Or set up Neo4j AuraDB

### Slow Performance?

**Solutions:**
- Upgrade to HF Pro ($9/month)
- Optimize queries
- Add caching

---

## Alternative: Docker Deployment

Want to run locally first?

```cmd
docker-compose -f deployment\docker-compose.yml up -d
```

Access at: http://localhost:7860

---

## Need Help?

### Documentation
- 📖 **Detailed Guide**: `deployment/DEPLOYMENT_GUIDE.md`
- 📋 **Summary**: `DEPLOYMENT_SUMMARY.md`
- 🎯 **Full Guide**: `HUGGINGFACE_DEPLOYMENT.md`

### Support
- 💬 Open GitHub issue
- 🤝 Ask in HF Discussions
- 📧 Contact team

---

## What You Get

### Interactive Web Interface
- 💬 Natural language queries
- 🔀 Toggle KG/Vector retrieval
- 📊 Real-time results
- 📚 Source citations
- 📈 Statistics display

### Powerful Features
- 🧠 Hybrid RAG (KG + Vector)
- 🔗 Multi-hop reasoning
- 🎯 Intelligent routing
- 📖 Explainable AI
- 🔍 Research gap analysis

---

## Cost

### Free Tier
- ✅ HF Space (CPU)
- ✅ Neo4j AuraDB (free tier)
- **Total: $0/month**

### Production
- 💰 HF Pro: $9/month
- 💰 Neo4j: $65/month
- **Total: $74/month**

---

## Success Checklist

- [ ] HF token obtained
- [ ] Token set in environment
- [ ] Deployment script run
- [ ] Space created successfully
- [ ] Environment variables configured
- [ ] Build completed
- [ ] Test queries work
- [ ] Results display correctly

---

## Next Steps

1. ✅ **Deploy** - You just did this!
2. 🔧 **Configure** - Add environment variables
3. 🧪 **Test** - Try example queries
4. 🎨 **Customize** - Update interface
5. 📊 **Monitor** - Check usage
6. 🚀 **Share** - Promote your Space!

---

## Quick Commands Reference

**Deploy:**
```cmd
deployment\deploy.bat
```

**Test:**
```cmd
python deployment\test_deployment.py
```

**Install Dependencies:**
```cmd
deployment\install_dependencies.bat
```

**Docker:**
```cmd
docker-compose -f deployment\docker-compose.yml up -d
```

---

## 🎉 Congratulations!

You've successfully deployed BodhiRAG to Hugging Face!

Your Space URL:
```
https://huggingface.co/spaces/YOUR_USERNAME/bodhirag-space-biology
```

**Share it with the world!** 🌍

---

**Built for NASA Space Apps Challenge 2025** 🚀

**Questions?*