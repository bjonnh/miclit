import itrmicfit.engine as imf_engine
import itrmicfit.plotting as imf_plotting

engine = imf_engine.Engine()
engine.load_file("data/test_data_multirow.xlsx")
engine.fit()
