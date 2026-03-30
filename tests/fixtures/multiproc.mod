MODULE MultiProcTest
  CONST robtarget p10 := [[100,0,0],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p20 := [[200,0,0],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p30 := [[300,0,0],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p40 := [[400,0,0],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
  CONST robtarget p50 := [[500,0,0],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];

  PROC main()
    MoveL p10, v100, fine, tool0;
    MoveL p20, v100, fine, tool0;
  ENDPROC

  PROC path2()
    MoveJ p30, v200, z10, tool0;
    MoveL p40, v100, fine, tool0;
    MoveL p50, v100, fine, tool0;
  ENDPROC
ENDMODULE
