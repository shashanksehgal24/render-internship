commands to run from GPT (shashank sehgal)

1:-  
        Remove-Item -Recurse -Force .venv


2:-     
        python -m venv .venv
        .venv\Scripts\Activate.ps1

3:-
        python -m pip install --upgrade pip setuptools wheel
        python -m pip install --upgrade --force-reinstall --no-cache-dir numpy pandas scipy scikit-learn joblib flask


4:- 
        python -c "import numpy; print('numpy ok', numpy.__version__)"


5:- 
        python app.py
