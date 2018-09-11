# dic = {'1': 'a', '2': None}
# dic2 = {'1': 'a', '2': None, '3':''}
#
# if (dic.keys() != dic2.keys()):
# 	print("no")
#
# if (dic.keys() == dic2.keys()):
# 	print("dz")
#
# li1 = ['1', '2', '4']
# li2 = ['1', '4', '2']
#
# print(sorted(li2))
# print(li2)
#
import sys
import ast

def main(argv):
	from firebase import firebase

	# firebase = firebase.FirebaseApplication("https://culturesystem-5f82b.firebaseio.com/")
	firebase = firebase.FirebaseApplication("https://culturetest-pso.firebaseio.com/")

	getData = firebase.get('/test/setup', None)
	print(type(getData["channels"]))

	channels = ast.literal_eval(getData["channels"])
	print(type(channels))

if __name__ == "__main__":
	main(sys.argv)
