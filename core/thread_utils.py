from PySide6.QtCore import QThread

def run_in_thread(worker, thread_list=None):
    """
    Standardizes QThread setup and lifecycle management to eliminate boilerplate.
    Automatically handles moving the worker to the thread, connecting cleanup signals,
    and starting the execution.
    
    Args:
        worker: A QObject instance with a `run()` method.
        thread_list: Optional list to store the thread to prevent garbage collection.
        
    Returns:
        The started QThread instance.
    """
    thread = QThread()
    worker.moveToThread(thread)
    
    # Keep a reference to prevent the worker from being garbage collected prematurely
    thread._worker = worker
    
    # Connect start trigger
    thread.started.connect(worker.run)
    
    # Connect standard cleanup signals
    # Support both explicit worker.signals.finished and direct worker.finished
    if hasattr(worker, 'signals') and hasattr(worker.signals, 'finished'):
        worker.signals.finished.connect(thread.quit)
        worker.signals.finished.connect(worker.deleteLater)
    elif hasattr(worker, 'finished'):
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        
    thread.finished.connect(thread.deleteLater)
    
    if thread_list is not None:
        thread_list.append(thread)
        
    thread.start()
    return thread
