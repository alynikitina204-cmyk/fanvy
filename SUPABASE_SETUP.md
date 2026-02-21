# Supabase Storage Setup Guide

## Step 1: Configure Credentials

1. Open `config.py`
2. Replace these values with your Supabase project details:
   - `SUPABASE_URL`: Your project URL (Settings → API → Project URL)
   - `SUPABASE_KEY`: Your anon/public key (Settings → API → anon/public key)

## Step 2: Create Storage Buckets

Go to your Supabase Dashboard → Storage and create these buckets:

1. **avatars** - For user profile pictures
   - Make it PUBLIC (users need to view avatars)
   
2. **uploads** - For post images
   - Make it PUBLIC
   
3. **music** - For music files
   - Make it PUBLIC
   
4. **stories** - For story images/videos
   - Make it PUBLIC
   
5. **images** - For photo album images
   - Make it PUBLIC

### How to create a bucket:
1. Click "New bucket"
2. Enter bucket name (e.g., "avatars")
3. Toggle "Public bucket" to ON
4. Click "Create bucket"

## Step 3: Set Storage Policies (Optional)

For each bucket, you can add policies:
- Allow authenticated users to upload
- Allow anyone to read (for public buckets)

Example policy for uploads:
```sql
-- Allow anyone to read files
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING (bucket_id = 'avatars');

-- Allow authenticated users to upload
CREATE POLICY "Authenticated Upload"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'avatars');
```

## Step 4: Test the Integration

Once configured, your uploads will automatically go to Supabase Storage instead of local `static/` folders.

### Benefits:
✅ Cloud storage - no local disk usage
✅ CDN delivery - faster image loading
✅ Scalable - handles any number of files
✅ Secure - configurable access policies

## Migration Plan (Optional)

To migrate existing files from `static/` to Supabase:

1. Keep `static/` folders as backup
2. New uploads go to Supabase automatically
3. Old files load from `static/` until migrated
4. Use Supabase CLI to bulk upload existing files

## Need Help?

If you encounter issues:
1. Check Supabase Dashboard → Logs
2. Verify bucket names match config.py
3. Ensure buckets are public
4. Check API key permissions
