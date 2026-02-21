# Quick Start Guide - LearnSocial iOS

## ⚡ Fastest Way to Test (5 minutes)

### Step 1: Start Flask Server
```bash
cd /Users/hk/learnsocial
python3 app.py
```
Keep this terminal running!

### Step 2: Create Xcode Project

1. **Open Xcode** (from Applications or Spotlight)

2. **Click** "Create New Project"

3. **Select Template:**
   - Choose **iOS** tab at the top
   - Select **App** template
   - Click **Next**

4. **Fill Project Details:**
   - Product Name: `LearnSocial`
   - Team: Select your Apple ID (or None for simulator only)
   - Organization Identifier: `com.learnsocial` 
   - Interface: **SwiftUI** 
   - Language: **Swift**
   - Uncheck all checkboxes (Core Data, Tests, etc.)
   - Click **Next**

5. **Save Location:**
   - Choose Desktop or Documents
   - Click **Create**

### Step 3: Replace Files

In Xcode's left sidebar (Navigator), you'll see these files:
- `LearnSocialApp.swift`
- `ContentView.swift`
- A folder called `Assets.xcassets`
- **Info.plist** may not be visible

**Delete** the default `LearnSocialApp.swift` and `ContentView.swift`

**Drag and drop** these files from `ios-app` folder into your Xcode project:
- `LearnSocialApp.swift` ✅
- `ContentView.swift` ✅

**For Info.plist:**
- Click on the **project name** at the very top of the left sidebar (the blue icon)
- Select the **LearnSocial** target in the main area
- Go to the **Info** tab
- Click the little "+" icon at the bottom and add:
  - **App Transport Security Settings** (Dictionary)
    - Inside it, add: **Allow Arbitrary Loads** → YES (Boolean)
    - Inside it, add: **Allow Local Networking** → YES (Boolean)

### Step 4: Run the App

1. At the top of Xcode, click the device selector (next to "LearnSocial")
2. Choose **iPhone 15 Pro** (or any iPhone simulator)
3. Press **⌘ + R** OR click the **▶️ Play** button
4. Wait for simulator to launch (first time takes 1-2 minutes)
5. Your LearnSocial web app will open inside the iOS app! 🎉

## 📝 Troubleshooting

**Problem:** "Could not connect to the server"
- **Solution:** Make sure Flask is running on `http://127.0.0.1:5000`

**Problem:** "No developer identity found"  
- **Solution:** In Xcode, go to Project Settings → Signing & Capabilities → Team → Select your Apple ID

**Problem:** Simulator is slow
- **Solution:** Choose iPhone SE (smaller screen = faster) or use your real iPhone

## 📱 Test on Your Real iPhone

1. **Plug in your iPhone** via USB
2. **Unlock** your iPhone
3. In Xcode, **select your iPhone** from device menu (it will appear at the top)
4. **Update the URL** in `ContentView.swift`:
   - Find your Mac's IP address:
     ```bash
     ifconfig | grep "inet " | grep -v 127.0.0.1
     ```
   - Change `"http://127.0.0.1:5000"` to `"http://YOUR_MAC_IP:5000"`
5. **Start Flask with network access:**
   ```bash
   python3 app.py --host=0.0.0.0
   ```
6. **Click Run** in Xcode
7. On iPhone: Settings → General → Device Management → Trust your developer account

## 🎨 Customization Ideas

- Add an app icon (drag image into Assets.xcassets)
- Change background color while loading
- Add pull-to-refresh
- Enable offline mode

## ⚠️ Important Notes

- This is a **development test only**
- Don't submit to App Store (violates guidelines for wrapper apps)
- The original Flask project is **unchanged** - this is totally separate
- For production, consider native iOS development or React Native/Flutter

---

Need help? Check the detailed README.md in this folder.
