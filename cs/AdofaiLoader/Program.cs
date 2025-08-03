using System;
using System.Diagnostics;

if (args.Length < 1)
{
    Console.WriteLine("Usage: AdofaiLoader <path.adofai>");
    return;
}

string path = args[0];
string pyCode = "from adofaipy import LevelDict;import sys;lvl=LevelDict(sys.argv[1]);print(len(lvl.getActions(lambda a:a.get('eventType')=='MoveCamera')))";
var psi = new ProcessStartInfo("python", $"-c \"{pyCode}\" \"{path}\"")
{
    RedirectStandardOutput = true,
    RedirectStandardError = true,
    UseShellExecute = false,
    CreateNoWindow = true
};
try
{
    using var proc = Process.Start(psi);
    string output = proc!.StandardOutput.ReadToEnd();
    string err = proc.StandardError.ReadToEnd();
    proc.WaitForExit();
    if (proc.ExitCode == 0)
    {
        Console.WriteLine($"MoveCamera actions: {output.Trim()}");
    }
    else
    {
        Console.WriteLine("Python error: " + err);
    }
}
catch (Exception ex)
{
    Console.WriteLine("Failed to run python: " + ex.Message);
}
