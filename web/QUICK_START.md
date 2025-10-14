# ⚡ TOM v3.0 - Quick Start Guide

## 🚀 **In 5 Minuten lauffähig**

### **1. Terminal öffnen & Projekt laden**
```bash
cd "G:\Meine Ablage\_________FAMO\_____Tom-Telefonassistent_3-0"
```

### **2. Python Environment**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### **3. Frontend starten**
```bash
cd web\dashboard
npm install
npm run dev
```

### **4. Hybrid Server starten**
```bash
# Neues Terminal
cd "G:\Meine Ablage\_________FAMO\_____Tom-Telefonassistent_3-0\infra"
python hybrid_server.py
```

### **5. Browser öffnen**
```
http://localhost:5173
```

---

## ✅ **Fertig!**

- **Frontend:** http://localhost:5173
- **WebSocket:** ws://localhost:8080
- **Mikrofon:** Auswählen und testen
- **Pipeline:** WhisperX → Ollama → Piper

---

## 🔧 **Falls etwas nicht geht:**

### **Port 8080 belegt:**
```bash
netstat -ano | findstr ":8080"
taskkill /PID <PID> /F
```

### **Ollama nicht da:**
```bash
ollama serve
ollama list
```

### **Node Modules Problem:**
```bash
cd web\dashboard
rm -rf node_modules
npm install
```

---

**Das war's! 🎉**
