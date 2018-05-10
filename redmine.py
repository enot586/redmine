"""генерация отчетов по задачам"""
import requests
import re
import datetime
import argparse
import sys
import os
import fnmatch
import pickle
import concurrent.futures

def replacing_js(txt, url_redmine):
	"""замещаем ссылки на скрипты скриптами"""
	try:
		temp = re.compile('<script.*src=\".*\".*</script>')
		m = temp.search(txt)
		while ( not (m is None) ):
			k = re.search( 'src=\".*\"', m.group(0) )
			#print( k.group(0)[5:-1] )
			js = requests.get( url_redmine+k.group(0)[5:-1] )
			txt = txt[0:m.start(0)]+'<script>'+js.text+'</script>'+txt[m.end(0):]
			m = temp.search(txt)
		
		return txt		
	except Exception as e:
		print('Error: replacing_js')
		print(e)
		raise
		
def replacing_css(txt, url_redmine):
	"""замещаем ссылки реальным содержимым таблиц"""
	try:
		temp = re.compile('<link.*rel=\"stylesheet\".*href=\".*\".*>')
		m = temp.search(txt)
		while ( not (m is None) ):
			k = re.search( 'href=\".*\"', m.group(0) )
			#print( k.group(0)[6:-1] )
			js = requests.get( url_redmine+k.group(0)[6:-1] )
			txt = txt[0:m.start(0)]+'<style>'+js.text+'</style>'+txt[m.end(0):]
			m = temp.search(txt)
		
		return txt		
	except Exception as e:
		print('Error: replacing_css')
		print(e)
		raise

def get_users(redmine_user, redmine_pass, url_redmine, users):
	"""получаем первых 200 пользователей редмайн"""
	for i in range(0, 200):
		user = requests.get( url_redmine+'/redmine/users/'+str(i)+'.json', auth=(redmine_user, redmine_pass) )
		if user.status_code == 200:
			jsonUser = user.json()
			users[ jsonUser['user']['id'] ] = jsonUser['user']
		
def get_report(redmine_user,redmine_pass, url_redmine, id, users, days, suffix, path):
	"""создаем отчет по задачам"""
	try:
		r = requests.get( url_redmine+'/redmine/issues?assigned_to_id='+str(id)+'&status_id=5&due_date=\u003et-{:d}'.format(days), auth=(redmine_user, redmine_pass) ) 
		
		html = r.text
		html = replacing_js(html, url_redmine)
		html = replacing_css(html, url_redmine)
		
		with open(path+'\\'+users[id]['lastname']+'_'+suffix+'.html','w', encoding='utf-8') as f:
			f.write(html)
	except Exception as e:
		print( '[{:d}][{:s}] ERROR: {:s}'.format( id, users[id]['lastname'], str(e) ) )
		raise
	else:
		print( '[{:d}][{:s}] SUCCESS'.format( id, users[id]['lastname'] ) )
		
def get_su_id(users, target_users):
	"""получить список идентификаторов для целевого списка пользователей"""
	#список пользователей по которым генерируем отчеты
	result = []
	
	for key,value in users.items():
		if value['lastname'].lower() in target_users:
			result.append( key )
	return result
	
def create_month_report(redmine_user, redmine_pass, url_redmine, users, ids, suff, path):
	"""генерируем месячный отчет"""
	for i in ids:
		get_report(redmine_user, redmine_pass, url_redmine, i, users, 31, suff, path)

def create_month_report_(redmine_user, redmine_pass, url_redmine, users, id, suff, path):
	"""генерируем месячный отчет для параллельного выполнения"""
	get_report(redmine_user, redmine_pass, url_redmine, id, users, 31, suff, path)
		
def create_q_report(redmine_user, redmine_pass, url_redmine, users, ids, suff, path):
	"""генерируем квартальный отчет"""
	for i in ids:
		get_report(redmine_user, redmine_pass, url_redmine, i, users, 95, suff, path)

def create_q_report_(redmine_user, redmine_pass, url_redmine, users, id, suff, path):
	"""генерируем квартальный отчет для параллельного выполнения"""
	get_report(redmine_user, redmine_pass, url_redmine, id, users, 95, suff, path)		
		
def create_half_report(redmine_user, redmine_pass, url_redmine, users, ids, suff, path):
	"""генерируем полугодовой отчет"""
	for i in ids:
		get_report(redmine_user, redmine_pass, url_redmine, i, users, 185, suff, path)
		
def create_half_report_(redmine_user, redmine_pass, url_redmine, users, id, suff, path):
	"""генерируем полугодовой отчет для параллельного выполнения"""
	get_report(redmine_user, redmine_pass, url_redmine, id, users, 185, suff, path)		
	
def get_all_users_list(redmine_user, redmine_pass, url_redmine, users, force_update):
	'''
	если установлен ключ force_update производим обновление списка пользователей безусловно
	если список пользователей уже когда-то получен то берем его из файлика users.pickle, это несколько быстрее
	'''
	pickle_file = os.path.dirname( os.path.abspath(__file__) )+r'\\users.pickle'
	
	if force_update or ( not os.path.exists(pickle_file) ):
		#получаем всех пользователей redmine, выполняется долго!
		get_users(redmine_user, redmine_pass, url_redmine, users )
		
		#создаем файлик чтобы больше не ждать
		with open(pickle_file, 'wb') as f:
			pickle.dump(users, f, pickle.HIGHEST_PROTOCOL)
	else:
		with open(pickle_file, 'rb') as f:
			users = pickle.load(f)

	return users		
	
def create_reports(redmine_user, redmine_pass, url_redmine, users, ids, j, p):
	"""
	генерируем все виды отчетов в зависимости от текущей даты.
	Запускасть приложение необходимо в последний день месяца, для корректной генерации квартальных и полугодовых отчетов
	"""
	d = datetime.date.today()
	
	month = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
	
	with concurrent.futures.ProcessPoolExecutor(max_workers=j) as executor:
		for id in ids:
			#генерируем месячные отчеты
			executor.submit(create_month_report_, 
							redmine_user, redmine_pass, url_redmine, 
							users, id, 
							str(d.year)+'_'+ month[d.month-1], p)
			
			#генерируем квартальные отчеты
			if ( d.month in [3, 6, 9, 12] ):
				executor.submit(create_q_report_, 
								redmine_user, redmine_pass, url_redmine, 
								users, id, 
								str(d.year)+'_'+'Q'+str(int(d.month/3)), p)
								
			#генерируем полугодовые отчеты
			if ( d.month in [6, 12] ):
				s = ''
				if (d.month == 6):
					s = '12'
				else:
					s = '34'
					
				executor.submit(create_half_report_, redmine_user, redmine_pass, url_redmine, users, id, str(d.year)+'_'+'Q'+s, p)
	
if __name__ == '__main__':	
	try:
		parser = argparse.ArgumentParser(description='Генерация отчетов Redmine по текущим задачам')
		
		parser.add_argument('-user', metavar='<user name>', required=True, help='Имя пользователя(логин) в Redmine')		

		parser.add_argument('-pas', metavar='<password>', required=True, help='Пароль пользователя Redmine')		
		
		parser.add_argument('-p', metavar='<path>', help='Абсолютный путь, где будут созданы отчеты. Если ключ -p=default, отчеты будут сгенерированы в папку по умолчанию \"<INSERT DEFAULT PATH HERE>\"')	
		
		parser.add_argument('-t', metavar='<lastname>', nargs='*', help='Список фамилий пользователей(заданных в Redmine) для которых будут генерироваться отчеты. По умолчанию генерируем отчеты для членов сектора СУ.')	

		parser.add_argument('-update', action='store_true', help='Безусловно обновляем список пользователей запрашивая у сервера Redmine. Список будет сохранен в users.pickle. Список будет запрошен автоматически при отсутсвии users.pickle в рабочем каталоге. По умолчанию список берется из файла users.pickle')		
		
		parser.add_argument('-j', metavar='X', type=int, nargs='?', default=4, help='Количество параллельных потоков для выполнения http запросов на сервер Redmine\'s. По умолчанию j=4')
		
		parser.add_argument('-url_redmine' ,metavar='<url:port>', default='<REDMINE_URL:PORT>', help='Адрес и порт сервера Redmine. По умолчанию используется \"<REDMINE_URL:PORT>\".' )
					
		#аргументы берутся из консоли
		input = parser.parse_args()	
		
		'''
		Если 
		-p не задан используем в качестве пути назначения текущую папку, 
		-p=default, то в качестве пути назанчения используется стандартный адрес сетевой папки на сервере для отчетов <INSERT DEFAULT PATH HERE> 
		-p=<path> используется заданный в ключе путь
		'''
		if (input.p == None):
			input.p = os.path.dirname( os.path.abspath(__file__) )
		else:
			if (input.p == 'default'):
				default_network_path = r'<INSERT DEFAULT PATH HERE>'
				default_network_path+= str(datetime.date.today().year)+r'\\'

				m = datetime.date.today().month
				
				if m < 10:
					filename = '0'+str(datetime.date.today().month) 
				else:
					filename = str(datetime.date.today().month) 
				
				filename+= '_'
				
				for file in os.listdir(default_network_path):
					if fnmatch.fnmatch(file, filename+'*'):
						input.p = default_network_path+file+r'\\'
						print(input.p)
						break
				else:
					input.p = os.path.dirname( os.path.abspath(__file__) )
					
			if not os.path.exists(input.p):
				print( "ERROR: Path \"{}\" does''t exist".format(input.p) )
				sys.exit()
		
		#получаем список всех пользователей редмайн, из файла, либо запрашивая у сервера, если файл не найден
		all_users = {}
		all_users = get_all_users_list(input.user, input.pas, input.url_redmine, all_users, input.update)
		
		target_users = []
		if (input.t is None):
			#если целевая группа не задана, берем список членов сектора СУ
			target_users = ['DEFAULT_USER1',
							'DEFAULT_USER2',
							'DEFAULT_USER3',
							'DEFAULT_USER4',
							'DEFAULT_USER5',
							'DEFAULT_USER6']
		else:
			target_users = [x.lower() for x in input.t]
		
		#получаем идентификтаоры пользователей Redmine для целевой группы пользователей		
		users_su_id = get_su_id(all_users, target_users)
		
		#генерируем отчеты для целевой группы пользователей
		create_reports(input.user, input.pas, input.url_redmine, all_users, users_su_id, input.j, input.p)
		
	except Exception as e:
		print( 'ERROR: {:s}'.format( str(e) ) )
