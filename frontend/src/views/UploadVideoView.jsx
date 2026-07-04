import ThemeToggle from '../components/ThemeToggle.jsx'

export default function UploadVideoView() {
  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold">Batch Processing</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Process multiple images or videos for batch detection.
        </p>

        <div className="mt-8 rounded-lg border bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Batch Upload</h3>
          <div className="mt-4">
            <input
              type="file"
              accept="image/*,video/*"
              multiple
              className="block w-full text-sm text-slate-500 dark:text-slate-400 file:mr-4 file:rounded-lg file:border-0 file:bg-green-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-green-700 hover:file:bg-green-100 dark:file:bg-green-900 dark:file:text-green-200 dark:hover:file:bg-green-800"
            />
          </div>
          <div className="mt-4 flex gap-4">
            <button className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700">
              Process Batch
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}