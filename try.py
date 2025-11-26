from werkzeug.security import generate_password_hash, check_password_hash
pwd = generate_password_hash('1', method="pbkdf2:sha256:200000")
hash_pwd = 'pbkdf2:sha256:200000$LvN7mk98a8CwsZA0$c4f84b00267ab20752157c06540f542c02c6cd6ed1fd4326cc0354e067cf14'
if check_password_hash(hash_pwd, ""):
    print("Password match")
else:
    print("Password do not match")
if pwd == hash_pwd:
    print("Hashes match")
else:
    print("Hashes do not match")
if check_password_hash(pwd,'1'):
    print("Generated hash matches password")